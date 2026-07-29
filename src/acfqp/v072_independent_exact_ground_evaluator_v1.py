"""Standalone exact H=2 ground evaluator for V0-072.

This module is deliberately independent of every production RAPM, robust or
lazy planner, source prior, campaign planner, and cached policy result.  Its
K4/K5 development controls remain domain-separated and unchanged.

The registered evaluator has a second, production-only surface.  It accepts
only the exact remote-main anchor, one of the three frozen public contexts, and
an exact typed operational terminal/selected-policy pair.  Transition
probabilities are never accepted from a caller: every H=2 row is reconstructed
through ``heldout_graph_transition_observer_v2.evaluation_only_exact_atoms_v2``.
The operational terminal factory accepts only a private authority minted from
an independently verified registered runtime result.  The selected abstract
policy is deterministic.  A fixed concretizer may realize that semantic action
as an exact uniform mixture over distinct ground actions; that is frozen
environment/action-realization randomness, not policy randomization.  The
exact ground comparator remains deterministic.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
from itertools import combinations, product
from fractions import Fraction
from typing import TYPE_CHECKING, Any, Mapping

from .phase3e_ids import canonical_json_bytes, parse_content_id
from . import heldout_graph_transition_observer_v2 as registered_observer
from . import transfer_guided_acquisition_preregistration_v1 as registered_prereg
from . import v072_final_preregistration_authority_v1 as final_authority

if TYPE_CHECKING:
    from .v072_registered_operational_terminal_authority_v1 import (
        RegisteredEvaluatorTerminalMintAuthorityV1,
    )


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.36.0"
PROFILE_KEY = "v072_independent_exact_ground_evaluator_v1"
HORIZON = 2
EVALUATION_LANE = "STANDALONE_EVALUATION_ONLY"
DEVELOPMENT_SCOPE = "DEVELOPMENT_K4_K5_CONTROL_ONLY"
REGISTERED_EVALUATION_ALLOWED = True
REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED = True
REGISTERED_OPERATIONAL_TERMINAL_BLOCKER = (
    "REGISTERED_VERIFIED_RUNTIME_RESULT_REQUIRED"
)
UNREACHABLE_POLICY_RULE = (
    "CANONICALLY_OMIT_ACTION_ASSIGNMENTS_UNREACHABLE_UNDER_ROOT_ACTION"
)


class V072IndependentExactGroundEvaluationViolation(ValueError):
    """An exact-type, identity, recurrence, or result invariant failed."""


class RegisteredIndependentExactGroundEvaluationLocked(RuntimeError):
    """Registered evaluation is unavailable before both future authorities."""


DOMAIN_TAGS = {
    "development_anchor": (
        "acfqp:v072-independent-exact-ground-development-anchor:v1"
    ),
    "development_context": (
        "acfqp:v072-independent-exact-ground-development-context:v1"
    ),
    "development_query": (
        "acfqp:v072-independent-exact-ground-development-query:v1"
    ),
    "development_law": (
        "acfqp:v072-independent-exact-ground-development-law:v1"
    ),
    "development_terminal": (
        "acfqp:v072-independent-exact-ground-development-terminal:v1"
    ),
    "state": "acfqp:v072-independent-exact-ground-state:v1",
    "action": "acfqp:v072-independent-exact-ground-action:v1",
    "transition": "acfqp:v072-independent-exact-ground-transition:v1",
    "row": "acfqp:v072-independent-exact-ground-row:v1",
    "child_decision": (
        "acfqp:v072-independent-exact-ground-child-decision:v1"
    ),
    "policy": "acfqp:v072-independent-exact-ground-policy:v1",
    "work": "acfqp:v072-independent-exact-ground-evaluation-work:v1",
    "result": "acfqp:v072-independent-exact-ground-result:v1",
    "replay_verification": (
        "acfqp:v072-exact-ground-same-implementation-replay-verification:v1"
    ),
    "registered_occurrence": (
        "acfqp:v072-registered-exact-ground-occurrence:v1"
    ),
    "registered_operational_child_decision": (
        "acfqp:v072-registered-operational-child-decision:v1"
    ),
    "registered_fixed_kappa_decision": (
        "acfqp:v072-registered-fixed-kappa-decision:v1"
    ),
    "registered_operational_policy": (
        "acfqp:v072-registered-operational-selected-policy:v1"
    ),
    "registered_operational_terminal": (
        "acfqp:v072-registered-occurrence-operational-terminal:v1"
    ),
    "registered_operational_terminal_policy_bundle": (
        "acfqp:v072-registered-operational-terminal-policy-bundle:v1"
    ),
    "registered_row": "acfqp:v072-registered-exact-ground-row:v1",
    "registered_policy_witness": (
        "acfqp:v072-registered-exact-ground-policy-witness:v1"
    ),
    "registered_kappa_policy_witness": (
        "acfqp:v072-registered-fixed-kappa-policy-witness:v1"
    ),
    "registered_work": (
        "acfqp:v072-registered-exact-ground-evaluation-work:v1"
    ),
    "registered_result": (
        "acfqp:v072-registered-independent-exact-ground-result:v1"
    ),
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("independent exact-ground domains must be unique")


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise V072IndependentExactGroundEvaluationViolation(
            str(error)
        ) from error
    return hashlib.sha256(domain + b"\x00" + body).hexdigest()


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V072IndependentExactGroundEvaluationViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        raise V072IndependentExactGroundEvaluationViolation(
            "exact evaluator accepts Fraction values only"
        )
    return {
        "numerator": value.numerator,
        "denominator": value.denominator,
    }


def _complete_edges(vertex_count: int) -> tuple[tuple[int, int], ...]:
    return tuple(combinations(range(vertex_count), 2))


@dataclass(frozen=True, slots=True)
class DevelopmentExactGroundSemanticAnchorV1:
    nonce: str = "v072-independent-exact-ground-k4-k5-control-anchor-v1"
    authority_scope: str = DEVELOPMENT_SCOPE
    registered_target_authority: bool = False

    def __post_init__(self) -> None:
        if (
            self.nonce
            != "v072-independent-exact-ground-k4-k5-control-anchor-v1"
            or self.authority_scope != DEVELOPMENT_SCOPE
            or self.registered_target_authority is not False
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "development exact-ground semantic anchor changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_development_anchor.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "nonce": self.nonce,
            "authority_scope": DEVELOPMENT_SCOPE,
            "registered_target_authority": False,
        }

    @property
    def anchor_id(self) -> str:
        return _content_id("development_anchor", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "anchor_id": self.anchor_id}


@dataclass(frozen=True, slots=True)
class DevelopmentExactGroundContextV1:
    control_key: str
    vertex_count: int
    edges: tuple[tuple[int, int], ...]
    rank_cap: int = 4
    authority_scope: str = DEVELOPMENT_SCOPE

    def __post_init__(self) -> None:
        expected_vertices = {
            "development_independent_exact_ground_k4_control_v1": 4,
            "development_independent_exact_ground_k5_control_v1": 5,
        }.get(self.control_key)
        if (
            expected_vertices is None
            or self.vertex_count != expected_vertices
            or self.edges != _complete_edges(expected_vertices)
            or self.rank_cap != 4
            or self.authority_scope != DEVELOPMENT_SCOPE
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "development context is not the frozen disjoint K4/K5 control"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_development_context.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "control_key": self.control_key,
            "vertex_count": self.vertex_count,
            "edges": [list(edge) for edge in self.edges],
            "rank_cap": self.rank_cap,
            "authority_scope": DEVELOPMENT_SCOPE,
            "registered_context_reused": False,
        }

    @property
    def context_id(self) -> str:
        return _content_id("development_context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def development_exact_ground_k4_context_v1(
) -> DevelopmentExactGroundContextV1:
    return DevelopmentExactGroundContextV1(
        "development_independent_exact_ground_k4_control_v1",
        4,
        _complete_edges(4),
    )


def development_exact_ground_k5_context_v1(
) -> DevelopmentExactGroundContextV1:
    return DevelopmentExactGroundContextV1(
        "development_independent_exact_ground_k5_control_v1",
        5,
        _complete_edges(5),
    )


@dataclass(frozen=True, slots=True)
class DevelopmentExactGroundQueryV1:
    context_id: str
    vertex_count: int
    rank_cap: int
    root_ranks: tuple[int, ...]
    risk_tolerance: Fraction
    horizon: int = HORIZON
    reward_profile: str = "CANONICAL_NORMALIZED_MERGE_REWARD"
    authority_scope: str = DEVELOPMENT_SCOPE

    def __post_init__(self) -> None:
        _cid(self.context_id, "development query context")
        if (
            self.vertex_count not in (4, 5)
            or self.rank_cap != 4
            or type(self.root_ranks) is not tuple
            or len(self.root_ranks) != self.vertex_count
            or any(
                type(rank) is not int or not 0 <= rank <= self.rank_cap
                for rank in self.root_ranks
            )
            or type(self.risk_tolerance) is not Fraction
            or not 0 <= self.risk_tolerance <= 1
            or self.horizon != HORIZON
            or self.reward_profile
            != "CANONICAL_NORMALIZED_MERGE_REWARD"
            or self.authority_scope != DEVELOPMENT_SCOPE
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "development exact-ground query is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_development_query.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "vertex_count": self.vertex_count,
            "rank_cap": self.rank_cap,
            "root_ranks": list(self.root_ranks),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "horizon": HORIZON,
            "reward_profile": self.reward_profile,
            "authority_scope": DEVELOPMENT_SCOPE,
        }

    @property
    def query_id(self) -> str:
        return _content_id("development_query", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_id": self.query_id}


def development_exact_ground_query_v1(
    *,
    context: DevelopmentExactGroundContextV1,
    root_ranks: tuple[int, ...],
    risk_tolerance: Fraction,
) -> DevelopmentExactGroundQueryV1:
    if type(context) is not DevelopmentExactGroundContextV1:
        raise V072IndependentExactGroundEvaluationViolation(
            "development query requires the exact context type"
        )
    return DevelopmentExactGroundQueryV1(
        context.context_id,
        context.vertex_count,
        context.rank_cap,
        root_ranks,
        risk_tolerance,
    )


@dataclass(frozen=True, slots=True)
class DevelopmentExactHiddenLawV1:
    context_id: str
    rank_cap: int
    rank_probabilities: tuple[tuple[int, Fraction], ...]
    law_role: str = "DEVELOPMENT_EXACT_HIDDEN_LAW_CONTROL_ONLY"

    def __post_init__(self) -> None:
        _cid(self.context_id, "development hidden-law context")
        if (
            self.rank_cap != 4
            or type(self.rank_probabilities) is not tuple
            or not self.rank_probabilities
            or tuple(
                rank for rank, _probability in self.rank_probabilities
            )
            != tuple(
                sorted(
                    {
                        rank
                        for rank, _probability in self.rank_probabilities
                    }
                )
            )
            or any(
                type(rank) is not int
                or not 1 <= rank <= self.rank_cap
                or type(probability) is not Fraction
                or probability <= 0
                for rank, probability in self.rank_probabilities
            )
            or sum(
                (
                    probability
                    for _rank, probability in self.rank_probabilities
                ),
                Fraction(0),
            )
            != 1
            or self.law_role
            != "DEVELOPMENT_EXACT_HIDDEN_LAW_CONTROL_ONLY"
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "development exact hidden law is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_development_law.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "rank_cap": self.rank_cap,
            "rank_probabilities": [
                {"rank": rank, "probability": _fdoc(probability)}
                for rank, probability in self.rank_probabilities
            ],
            "law_role": self.law_role,
            "registered_hidden_law_reused": False,
        }

    @property
    def law_id(self) -> str:
        return _content_id("development_law", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "law_id": self.law_id}


@dataclass(frozen=True, slots=True)
class DevelopmentExactGroundTerminalRefV1:
    anchor_id: str
    context_id: str
    query_id: str
    law_id: str
    logical_occurrence_id: str
    terminal_code: str = "DEVELOPMENT_CONTROL_READY_FOR_EVALUATION"
    authority_scope: str = DEVELOPMENT_SCOPE
    operational_campaign_terminal_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.anchor_id, "development terminal anchor"),
            (self.context_id, "development terminal context"),
            (self.query_id, "development terminal query"),
            (self.law_id, "development terminal law"),
            (
                self.logical_occurrence_id,
                "development terminal logical occurrence",
            ),
        ):
            _cid(value, field_name)
        if (
            self.terminal_code
            != "DEVELOPMENT_CONTROL_READY_FOR_EVALUATION"
            or self.authority_scope != DEVELOPMENT_SCOPE
            or self.operational_campaign_terminal_claimed is not False
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "development terminal reference changed scope"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_development_terminal.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "law_id": self.law_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "terminal_code": self.terminal_code,
            "authority_scope": DEVELOPMENT_SCOPE,
            "operational_campaign_terminal_claimed": False,
        }

    @property
    def terminal_ref_id(self) -> str:
        return _content_id("development_terminal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "terminal_ref_id": self.terminal_ref_id}


def development_exact_ground_terminal_ref_v1(
    *,
    anchor: DevelopmentExactGroundSemanticAnchorV1,
    context: DevelopmentExactGroundContextV1,
    query: DevelopmentExactGroundQueryV1,
    law: DevelopmentExactHiddenLawV1,
    logical_occurrence_id: str,
) -> DevelopmentExactGroundTerminalRefV1:
    if (
        type(anchor) is not DevelopmentExactGroundSemanticAnchorV1
        or type(context) is not DevelopmentExactGroundContextV1
        or type(query) is not DevelopmentExactGroundQueryV1
        or type(law) is not DevelopmentExactHiddenLawV1
        or query.context_id != context.context_id
        or law.context_id != context.context_id
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "development terminal binding is inconsistent"
        )
    return DevelopmentExactGroundTerminalRefV1(
        anchor.anchor_id,
        context.context_id,
        query.query_id,
        law.law_id,
        logical_occurrence_id,
    )


def _state_id(
    context_id: str,
    remaining_horizon: int,
    ranks: tuple[int, ...],
) -> str:
    return _content_id(
        "state",
        {
            "schema": "acfqp.v072_independent_exact_ground_state.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "remaining_horizon": remaining_horizon,
            "ranks": list(ranks),
        },
    )


def _action_id(
    context_id: str,
    source_state_id: str,
    remaining_horizon: int,
    action: tuple[int, int, int],
) -> str:
    return _content_id(
        "action",
        {
            "schema": "acfqp.v072_independent_exact_ground_action.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context_id,
            "source_state_id": source_state_id,
            "remaining_horizon": remaining_horizon,
            "action": list(action),
        },
    )


def _legal_actions(
    context: DevelopmentExactGroundContextV1,
    ranks: tuple[int, ...],
) -> tuple[tuple[int, int, int], ...]:
    return tuple(
        sorted(
            (first, second, survivor)
            for first, second in context.edges
            if ranks[first] > 0 and ranks[first] == ranks[second]
            for survivor in (first, second)
        )
    )


@dataclass(frozen=True, slots=True)
class ExactGroundTransitionV1:
    context_id: str
    query_id: str
    law_id: str
    source_state_id: str
    action_id: str
    remaining_horizon: int
    next_ranks: tuple[int, ...]
    probability: Fraction
    reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "transition context"),
            (self.query_id, "transition query"),
            (self.law_id, "transition law"),
            (self.source_state_id, "transition source state"),
            (self.action_id, "transition action"),
        ):
            _cid(value, field_name)
        if (
            self.remaining_horizon not in (1, HORIZON)
            or type(self.next_ranks) is not tuple
            or not self.next_ranks
            or any(type(rank) is not int or rank < 0 for rank in self.next_ranks)
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.reward) is not Fraction
            or not 0 <= self.reward <= 1
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.terminal != (
                self.failure or self.remaining_horizon == 1
            )
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact ground transition is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_independent_exact_ground_transition.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "law_id": self.law_id,
            "source_state_id": self.source_state_id,
            "action_id": self.action_id,
            "remaining_horizon": self.remaining_horizon,
            "next_ranks": list(self.next_ranks),
            "probability": _fdoc(self.probability),
            "reward": _fdoc(self.reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def transition_id(self) -> str:
        return _content_id("transition", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "transition_id": self.transition_id}


@dataclass(frozen=True, slots=True)
class ExactGroundRowV1:
    context_id: str
    query_id: str
    law_id: str
    source_state_id: str
    source_ranks: tuple[int, ...]
    remaining_horizon: int
    action: tuple[int, int, int]
    action_id: str
    transitions: tuple[ExactGroundTransitionV1, ...]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.context_id, "row context"),
            (self.query_id, "row query"),
            (self.law_id, "row law"),
            (self.source_state_id, "row source state"),
            (self.action_id, "row action"),
        ):
            _cid(value, field_name)
        if (
            type(self.source_ranks) is not tuple
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.action) is not tuple
            or len(self.action) != 3
            or type(self.transitions) is not tuple
            or not self.transitions
            or any(
                type(item) is not ExactGroundTransitionV1
                or item.context_id != self.context_id
                or item.query_id != self.query_id
                or item.law_id != self.law_id
                or item.source_state_id != self.source_state_id
                or item.action_id != self.action_id
                or item.remaining_horizon != self.remaining_horizon
                for item in self.transitions
            )
            or tuple(item.transition_id for item in self.transitions)
            != tuple(
                sorted(
                    {item.transition_id for item in self.transitions}
                )
            )
            or sum(
                (item.probability for item in self.transitions),
                Fraction(0),
            )
            != 1
            or len({item.reward for item in self.transitions}) != 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact ground row is incomplete or noncanonical"
            )

    @property
    def reward(self) -> Fraction:
        return self.transitions[0].reward

    @property
    def failure_probability(self) -> Fraction:
        return sum(
            (
                item.probability
                for item in self.transitions
                if item.failure
            ),
            Fraction(0),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_independent_exact_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "law_id": self.law_id,
            "source_state_id": self.source_state_id,
            "source_ranks": list(self.source_ranks),
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "action_id": self.action_id,
            "transition_ids": [
                item.transition_id for item in self.transitions
            ],
            "reward": _fdoc(self.reward),
            "failure_probability": _fdoc(self.failure_probability),
        }

    @property
    def row_id(self) -> str:
        return _content_id("row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "transitions": [
                item.to_document() for item in self.transitions
            ],
            "row_id": self.row_id,
        }


@dataclass(frozen=True, slots=True)
class ExactGroundChildDecisionV1:
    context_id: str
    state_id: str
    state_ranks: tuple[int, ...]
    action: tuple[int, int, int]
    action_id: str

    def __post_init__(self) -> None:
        _cid(self.context_id, "child-decision context")
        _cid(self.state_id, "child-decision state")
        _cid(self.action_id, "child-decision action")
        if (
            type(self.state_ranks) is not tuple
            or not self.state_ranks
            or type(self.action) is not tuple
            or len(self.action) != 3
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact child decision is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_child_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state_id,
            "state_ranks": list(self.state_ranks),
            "action": list(self.action),
            "action_id": self.action_id,
        }

    @property
    def child_decision_id(self) -> str:
        return _content_id("child_decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_decision_id": self.child_decision_id,
        }


@dataclass(frozen=True, slots=True)
class ExactGroundPolicyV1:
    anchor_id: str
    context_id: str
    query_id: str
    law_id: str
    terminal_ref_id: str
    root_action: tuple[int, int, int]
    root_action_id: str
    child_decisions: tuple[ExactGroundChildDecisionV1, ...]
    expected_reward: Fraction
    failure_probability: Fraction
    feasible: bool

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.anchor_id, "policy anchor"),
            (self.context_id, "policy context"),
            (self.query_id, "policy query"),
            (self.law_id, "policy law"),
            (self.terminal_ref_id, "policy terminal"),
            (self.root_action_id, "policy root action"),
        ):
            _cid(value, field_name)
        if (
            type(self.root_action) is not tuple
            or len(self.root_action) != 3
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not ExactGroundChildDecisionV1
                or item.context_id != self.context_id
                for item in self.child_decisions
            )
            or tuple(
                (item.state_ranks, item.action)
                for item in self.child_decisions
            )
            != tuple(
                sorted(
                    {
                        (item.state_ranks, item.action)
                        for item in self.child_decisions
                    }
                )
            )
            or len({item.state_id for item in self.child_decisions})
            != len(self.child_decisions)
            or type(self.expected_reward) is not Fraction
            or self.expected_reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
            or type(self.feasible) is not bool
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact deterministic contingent policy is malformed"
            )

    @property
    def semantic_policy_key(
        self,
    ) -> tuple[
        tuple[int, int, int],
        tuple[
            tuple[
                tuple[int, ...],
                tuple[int, int, int],
            ],
            ...,
        ],
    ]:
        return (
            self.root_action,
            tuple(
                (item.state_ranks, item.action)
                for item in self.child_decisions
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_independent_exact_ground_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "law_id": self.law_id,
            "terminal_ref_id": self.terminal_ref_id,
            "root_action": list(self.root_action),
            "root_action_id": self.root_action_id,
            "child_decision_ids": [
                item.child_decision_id for item in self.child_decisions
            ],
            "semantic_policy_key": {
                "root_action": list(self.root_action),
                "ordered_child_actions": [
                    {
                        "state_ranks": list(item.state_ranks),
                        "action": list(item.action),
                    }
                    for item in self.child_decisions
                ],
            },
            "expected_reward": _fdoc(self.expected_reward),
            "failure_probability": _fdoc(self.failure_probability),
            "feasible": self.feasible,
            "deterministic": True,
            "unreachable_policy_rule": UNREACHABLE_POLICY_RULE,
        }

    @property
    def policy_id(self) -> str:
        return _content_id("policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_decisions": [
                item.to_document() for item in self.child_decisions
            ],
            "policy_id": self.policy_id,
        }


@dataclass(frozen=True, slots=True)
class ExactGroundEvaluationWorkV1:
    exact_row_evaluations: int
    exact_positive_transition_outcomes: int
    deterministic_contingent_policies_enumerated: int
    feasible_policies_enumerated: int
    fraction_recurrence_evaluations: int
    operational_work_records_written: int = 0
    accepted_sample_draws: int = 0
    online_sample_endpoint_writes: int = 0
    source_prior_reads: int = 0
    production_model_builder_calls: int = 0
    production_planner_calls: int = 0
    production_policy_result_reads: int = 0
    execution_lane: str = EVALUATION_LANE

    def __post_init__(self) -> None:
        integer_values = (
            self.exact_row_evaluations,
            self.exact_positive_transition_outcomes,
            self.deterministic_contingent_policies_enumerated,
            self.feasible_policies_enumerated,
            self.fraction_recurrence_evaluations,
            self.operational_work_records_written,
            self.accepted_sample_draws,
            self.online_sample_endpoint_writes,
            self.source_prior_reads,
            self.production_model_builder_calls,
            self.production_planner_calls,
            self.production_policy_result_reads,
        )
        if (
            any(type(value) is not int or value < 0 for value in integer_values)
            or self.exact_row_evaluations <= 0
            or self.exact_positive_transition_outcomes
            < self.exact_row_evaluations
            or self.deterministic_contingent_policies_enumerated <= 0
            or self.feasible_policies_enumerated
            > self.deterministic_contingent_policies_enumerated
            or self.fraction_recurrence_evaluations
            != self.deterministic_contingent_policies_enumerated
            or any(value != 0 for value in integer_values[5:])
            or self.execution_lane != EVALUATION_LANE
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "standalone evaluation-only work does not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_independent_exact_ground_evaluation_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__
            },
        }

    @property
    def evaluation_work_id(self) -> str:
        return _content_id("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "evaluation_work_id": self.evaluation_work_id,
        }


class ExactGroundEvaluationStatusV1(str, Enum):
    FEASIBLE_OPTIMUM = "FEASIBLE_OPTIMUM"
    INFEASIBLE = "INFEASIBLE"


@dataclass(frozen=True, slots=True)
class IndependentExactGroundEvaluationResultV1:
    anchor: DevelopmentExactGroundSemanticAnchorV1
    context: DevelopmentExactGroundContextV1
    query: DevelopmentExactGroundQueryV1
    law: DevelopmentExactHiddenLawV1
    terminal_ref: DevelopmentExactGroundTerminalRefV1
    status: ExactGroundEvaluationStatusV1
    rows: tuple[ExactGroundRowV1, ...]
    policies: tuple[ExactGroundPolicyV1, ...]
    selected_policy_id: str | None
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    minimum_failure_probability: Fraction
    maximum_unconstrained_reward: Fraction
    work: ExactGroundEvaluationWorkV1
    execution_lane: str = EVALUATION_LANE
    operational_work_included: bool = False
    sample_endpoint_mutated: bool = False
    registered_result_claimed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.anchor) is not DevelopmentExactGroundSemanticAnchorV1
            or type(self.context) is not DevelopmentExactGroundContextV1
            or type(self.query) is not DevelopmentExactGroundQueryV1
            or type(self.law) is not DevelopmentExactHiddenLawV1
            or type(self.terminal_ref)
            is not DevelopmentExactGroundTerminalRefV1
            or type(self.status) is not ExactGroundEvaluationStatusV1
            or type(self.rows) is not tuple
            or not self.rows
            or type(self.policies) is not tuple
            or not self.policies
            or type(self.work) is not ExactGroundEvaluationWorkV1
            or self.execution_lane != EVALUATION_LANE
            or self.operational_work_included is not False
            or self.sample_endpoint_mutated is not False
            or self.registered_result_claimed is not False
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "independent exact-ground result has a malformed schema"
            )
        binding = (
            self.anchor.anchor_id,
            self.context.context_id,
            self.query.query_id,
            self.law.law_id,
            self.terminal_ref.terminal_ref_id,
        )
        if (
            self.query.context_id != self.context.context_id
            or self.query.vertex_count != self.context.vertex_count
            or self.query.rank_cap != self.context.rank_cap
            or self.law.context_id != self.context.context_id
            or self.law.rank_cap != self.context.rank_cap
            or (
                self.terminal_ref.anchor_id,
                self.terminal_ref.context_id,
                self.terminal_ref.query_id,
                self.terminal_ref.law_id,
            )
            != binding[:4]
            or any(
                (
                    row.context_id,
                    row.query_id,
                    row.law_id,
                )
                != binding[1:4]
                for row in self.rows
            )
            or any(
                (
                    policy.anchor_id,
                    policy.context_id,
                    policy.query_id,
                    policy.law_id,
                    policy.terminal_ref_id,
                )
                != binding
                for policy in self.policies
            )
            or tuple(row.row_id for row in self.rows)
            != tuple(sorted({row.row_id for row in self.rows}))
            or tuple(policy.policy_id for policy in self.policies)
            != tuple(
                sorted({policy.policy_id for policy in self.policies})
            )
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact-ground rows/policies were transplanted"
            )
        feasible = tuple(policy for policy in self.policies if policy.feasible)
        if any(
            policy.feasible
            != (policy.failure_probability <= self.query.risk_tolerance)
            for policy in self.policies
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "policy feasibility flags differ from the exact threshold"
            )
        minimum_risk = min(
            policy.failure_probability for policy in self.policies
        )
        maximum_reward = max(
            policy.expected_reward for policy in self.policies
        )
        if (
            self.minimum_failure_probability != minimum_risk
            or self.maximum_unconstrained_reward != maximum_reward
            or self.work.exact_row_evaluations != len(self.rows)
            or self.work.exact_positive_transition_outcomes
            != sum(len(row.transitions) for row in self.rows)
            or self.work.deterministic_contingent_policies_enumerated
            != len(self.policies)
            or self.work.feasible_policies_enumerated != len(feasible)
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "exact-ground result summary/work does not reconcile"
            )
        if self.status is ExactGroundEvaluationStatusV1.FEASIBLE_OPTIMUM:
            if (
                not feasible
                or self.selected_policy_id is None
                or self.optimal_expected_reward is None
                or self.optimal_failure_probability is None
            ):
                raise V072IndependentExactGroundEvaluationViolation(
                    "feasible result omits its exact optimum"
                )
            selected = tuple(
                policy
                for policy in feasible
                if policy.policy_id == self.selected_policy_id
            )
            expected_selected = min(
                feasible,
                key=lambda item: (
                    -item.expected_reward,
                    item.failure_probability,
                    item.semantic_policy_key,
                ),
            )
            if (
                len(selected) != 1
                or selected[0].policy_id != expected_selected.policy_id
                or selected[0].expected_reward
                != self.optimal_expected_reward
                or selected[0].failure_probability
                != self.optimal_failure_probability
                or selected[0].failure_probability
                > self.query.risk_tolerance
            ):
                raise V072IndependentExactGroundEvaluationViolation(
                    "selected exact-ground policy is stale or infeasible"
                )
        elif (
            feasible
            or self.selected_policy_id is not None
            or self.optimal_expected_reward is not None
            or self.optimal_failure_probability is not None
            or self.minimum_failure_probability <= self.query.risk_tolerance
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "infeasible exact-ground result carries a feasible policy"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_independent_exact_ground_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_id": self.anchor.anchor_id,
            "context_id": self.context.context_id,
            "query_id": self.query.query_id,
            "law_id": self.law.law_id,
            "terminal_ref_id": self.terminal_ref.terminal_ref_id,
            "status": self.status.value,
            "row_ids": [row.row_id for row in self.rows],
            "policy_ids": [policy.policy_id for policy in self.policies],
            "selected_policy_id": self.selected_policy_id,
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "minimum_failure_probability": _fdoc(
                self.minimum_failure_probability
            ),
            "maximum_unconstrained_reward": _fdoc(
                self.maximum_unconstrained_reward
            ),
            "evaluation_work_id": self.work.evaluation_work_id,
            "execution_lane": EVALUATION_LANE,
            "operational_work_included": False,
            "sample_endpoint_mutated": False,
            "registered_result_claimed": False,
            "development_scope": DEVELOPMENT_SCOPE,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())

    @property
    def selected_policy(self) -> ExactGroundPolicyV1 | None:
        if self.selected_policy_id is None:
            return None
        return next(
            policy
            for policy in self.policies
            if policy.policy_id == self.selected_policy_id
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "anchor": self.anchor.to_document(),
            "context": self.context.to_document(),
            "query": self.query.to_document(),
            "law": self.law.to_document(),
            "terminal_ref": self.terminal_ref.to_document(),
            "rows": [row.to_document() for row in self.rows],
            "policies": [policy.to_document() for policy in self.policies],
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }


def _validate_development_bindings(
    *,
    anchor: Any,
    context: Any,
    query: Any,
    law: Any,
    terminal_ref: Any,
) -> tuple[
    DevelopmentExactGroundSemanticAnchorV1,
    DevelopmentExactGroundContextV1,
    DevelopmentExactGroundQueryV1,
    DevelopmentExactHiddenLawV1,
    DevelopmentExactGroundTerminalRefV1,
]:
    if (
        type(anchor) is not DevelopmentExactGroundSemanticAnchorV1
        or type(context) is not DevelopmentExactGroundContextV1
        or type(query) is not DevelopmentExactGroundQueryV1
        or type(law) is not DevelopmentExactHiddenLawV1
        or type(terminal_ref) is not DevelopmentExactGroundTerminalRefV1
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "development exact-ground evaluator rejects duck types"
        )
    if (
        query.context_id != context.context_id
        or query.vertex_count != context.vertex_count
        or query.rank_cap != context.rank_cap
        or law.context_id != context.context_id
        or law.rank_cap != context.rank_cap
        or terminal_ref.anchor_id != anchor.anchor_id
        or terminal_ref.context_id != context.context_id
        or terminal_ref.query_id != query.query_id
        or terminal_ref.law_id != law.law_id
        or not _legal_actions(context, query.root_ranks)
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "development context/query/law/terminal binding is stale"
        )
    return anchor, context, query, law, terminal_ref


def _enumerate_row(
    *,
    context: DevelopmentExactGroundContextV1,
    query: DevelopmentExactGroundQueryV1,
    law: DevelopmentExactHiddenLawV1,
    ranks: tuple[int, ...],
    remaining_horizon: int,
    action: tuple[int, int, int],
) -> ExactGroundRowV1:
    legal = _legal_actions(context, ranks)
    if action not in legal:
        raise V072IndependentExactGroundEvaluationViolation(
            "exact recurrence received an illegal ground action"
        )
    source_state_id = _state_id(
        context.context_id,
        remaining_horizon,
        ranks,
    )
    action_id = _action_id(
        context.context_id,
        source_state_id,
        remaining_horizon,
        action,
    )
    first, second, survivor = action
    source_rank = ranks[first]
    board = list(ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(source_rank + 1, context.rank_cap)
    empty = tuple(index for index, rank in enumerate(board) if rank == 0)
    if not empty:
        raise V072IndependentExactGroundEvaluationViolation(
            "exact merge produced no spawn position"
        )
    reward = (
        Fraction(2 ** (source_rank + 1), 2 ** (context.rank_cap + 1))
        / HORIZON
    )
    probabilities: dict[tuple[tuple[int, ...], bool, bool], Fraction] = {}
    for position in empty:
        for spawn_rank, spawn_probability in law.rank_probabilities:
            successor = list(board)
            successor[position] = spawn_rank
            successor_ranks = tuple(successor)
            failure = not _legal_actions(context, successor_ranks)
            terminal = failure or remaining_horizon == 1
            key = (successor_ranks, failure, terminal)
            probabilities[key] = probabilities.get(key, Fraction(0)) + (
                Fraction(1, len(empty)) * spawn_probability
            )
    transitions = tuple(
        sorted(
            (
                ExactGroundTransitionV1(
                    context.context_id,
                    query.query_id,
                    law.law_id,
                    source_state_id,
                    action_id,
                    remaining_horizon,
                    successor_ranks,
                    probability,
                    reward,
                    failure,
                    terminal,
                )
                for (
                    successor_ranks,
                    failure,
                    terminal,
                ), probability in probabilities.items()
            ),
            key=lambda item: item.transition_id,
        )
    )
    return ExactGroundRowV1(
        context.context_id,
        query.query_id,
        law.law_id,
        source_state_id,
        ranks,
        remaining_horizon,
        action,
        action_id,
        transitions,
    )


def _evaluate_development_exact_ground(
    *,
    anchor: DevelopmentExactGroundSemanticAnchorV1,
    context: DevelopmentExactGroundContextV1,
    query: DevelopmentExactGroundQueryV1,
    law: DevelopmentExactHiddenLawV1,
    terminal_ref: DevelopmentExactGroundTerminalRefV1,
) -> IndependentExactGroundEvaluationResultV1:
    row_cache: dict[
        tuple[tuple[int, ...], int, tuple[int, int, int]],
        ExactGroundRowV1,
    ] = {}

    def row_for(
        ranks: tuple[int, ...],
        remaining_horizon: int,
        action: tuple[int, int, int],
    ) -> ExactGroundRowV1:
        key = (ranks, remaining_horizon, action)
        if key not in row_cache:
            row_cache[key] = _enumerate_row(
                context=context,
                query=query,
                law=law,
                ranks=ranks,
                remaining_horizon=remaining_horizon,
                action=action,
            )
        return row_cache[key]

    root_rows = tuple(
        row_for(query.root_ranks, HORIZON, action)
        for action in _legal_actions(context, query.root_ranks)
    )
    policies: list[ExactGroundPolicyV1] = []
    for root_row in root_rows:
        reachable_child_states = tuple(
            sorted(
                {
                    transition.next_ranks
                    for transition in root_row.transitions
                    if not transition.terminal
                }
            )
        )
        child_action_sets = tuple(
            _legal_actions(context, ranks)
            for ranks in reachable_child_states
        )
        if any(not actions for actions in child_action_sets):
            raise RuntimeError("active child has no legal action")
        assignments = (
            product(*child_action_sets)
            if child_action_sets
            else ((),)
        )
        for assigned_actions in assignments:
            decisions: list[ExactGroundChildDecisionV1] = []
            child_row_by_ranks: dict[
                tuple[int, ...],
                ExactGroundRowV1,
            ] = {}
            for ranks, action in zip(
                reachable_child_states,
                assigned_actions,
            ):
                child_row = row_for(ranks, 1, action)
                child_row_by_ranks[ranks] = child_row
                decisions.append(
                    ExactGroundChildDecisionV1(
                        context.context_id,
                        child_row.source_state_id,
                        ranks,
                        action,
                        child_row.action_id,
                    )
                )
            expected_reward = root_row.reward
            failure_probability = Fraction(0)
            for transition in root_row.transitions:
                if transition.failure:
                    failure_probability += transition.probability
                elif not transition.terminal:
                    child_row = child_row_by_ranks[transition.next_ranks]
                    expected_reward += (
                        transition.probability * child_row.reward
                    )
                    failure_probability += (
                        transition.probability
                        * child_row.failure_probability
                    )
            policies.append(
                ExactGroundPolicyV1(
                    anchor.anchor_id,
                    context.context_id,
                    query.query_id,
                    law.law_id,
                    terminal_ref.terminal_ref_id,
                    root_row.action,
                    root_row.action_id,
                    tuple(
                        sorted(
                            decisions,
                            key=lambda item: (
                                item.state_ranks,
                                item.action,
                            ),
                        )
                    ),
                    expected_reward,
                    failure_probability,
                    failure_probability <= query.risk_tolerance,
                )
            )
    policy_tuple = tuple(
        sorted(policies, key=lambda item: item.policy_id)
    )
    if len({item.policy_id for item in policy_tuple}) != len(policy_tuple):
        raise RuntimeError("exact policy enumeration produced duplicates")
    rows = tuple(sorted(row_cache.values(), key=lambda item: item.row_id))
    feasible = tuple(policy for policy in policy_tuple if policy.feasible)
    selected = (
        min(
            feasible,
            key=lambda item: (
                -item.expected_reward,
                item.failure_probability,
                item.semantic_policy_key,
            ),
        )
        if feasible
        else None
    )
    work = ExactGroundEvaluationWorkV1(
        len(rows),
        sum(len(row.transitions) for row in rows),
        len(policy_tuple),
        len(feasible),
        len(policy_tuple),
    )
    return IndependentExactGroundEvaluationResultV1(
        anchor,
        context,
        query,
        law,
        terminal_ref,
        (
            ExactGroundEvaluationStatusV1.FEASIBLE_OPTIMUM
            if selected is not None
            else ExactGroundEvaluationStatusV1.INFEASIBLE
        ),
        rows,
        policy_tuple,
        None if selected is None else selected.policy_id,
        None if selected is None else selected.expected_reward,
        None if selected is None else selected.failure_probability,
        min(policy.failure_probability for policy in policy_tuple),
        max(policy.expected_reward for policy in policy_tuple),
        work,
    )


def evaluate_development_independent_exact_ground_v1(
    *,
    anchor: Any,
    context: Any,
    query: Any,
    law: Any,
    terminal_ref: Any,
) -> IndependentExactGroundEvaluationResultV1:
    """Enumerate one disjoint development control with exact Fractions."""

    values = _validate_development_bindings(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal_ref,
    )
    return _evaluate_development_exact_ground(
        anchor=values[0],
        context=values[1],
        query=values[2],
        law=values[3],
        terminal_ref=values[4],
    )


@dataclass(frozen=True, slots=True)
class ExactGroundSameImplementationReplayVerificationV1:
    result_id: str
    deterministically_replayed_result_id: str
    context_id: str
    query_id: str
    law_id: str
    terminal_ref_id: str
    execution_lane: str = EVALUATION_LANE
    production_authority_called: bool = False
    operational_work_included: bool = False
    same_implementation_deterministic_replay: bool = True
    independent_verifier_implementation_claimed: bool = False
    separate_brute_force_golden_required: bool = True
    valid: bool = True

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.result_id, "verified result"),
            (
                self.deterministically_replayed_result_id,
                "deterministically replayed result",
            ),
            (self.context_id, "verified context"),
            (self.query_id, "verified query"),
            (self.law_id, "verified law"),
            (self.terminal_ref_id, "verified terminal"),
        ):
            _cid(value, field_name)
        if (
            self.result_id != self.deterministically_replayed_result_id
            or self.execution_lane != EVALUATION_LANE
            or self.production_authority_called is not False
            or self.operational_work_included is not False
            or self.same_implementation_deterministic_replay is not True
            or self.independent_verifier_implementation_claimed is not False
            or self.separate_brute_force_golden_required is not True
            or self.valid is not True
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "same-implementation replay claim is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_exact_ground_same_implementation_replay_"
                "verification.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "result_id": self.result_id,
            "deterministically_replayed_result_id": (
                self.deterministically_replayed_result_id
            ),
            "context_id": self.context_id,
            "query_id": self.query_id,
            "law_id": self.law_id,
            "terminal_ref_id": self.terminal_ref_id,
            "execution_lane": EVALUATION_LANE,
            "production_authority_called": False,
            "operational_work_included": False,
            "same_implementation_deterministic_replay": True,
            "independent_verifier_implementation_claimed": False,
            "separate_brute_force_golden_required": True,
            "valid": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("replay_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "verification_id": self.verification_id,
        }


def verify_development_exact_ground_same_implementation_replay_v1(
    *,
    anchor: Any,
    context: Any,
    query: Any,
    law: Any,
    terminal_ref: Any,
    claimed: Any,
) -> ExactGroundSameImplementationReplayVerificationV1:
    values = _validate_development_bindings(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal_ref,
    )
    if type(claimed) is not IndependentExactGroundEvaluationResultV1:
        raise V072IndependentExactGroundEvaluationViolation(
            "exact-ground result verifier rejects duck types"
        )
    recomputed = _evaluate_development_exact_ground(
        anchor=values[0],
        context=values[1],
        query=values[2],
        law=values[3],
        terminal_ref=values[4],
    )
    if claimed != recomputed or claimed.result_id != recomputed.result_id:
        raise V072IndependentExactGroundEvaluationViolation(
            "claimed exact-ground result/policy was transplanted or re-signed"
        )
    return ExactGroundSameImplementationReplayVerificationV1(
        claimed.result_id,
        recomputed.result_id,
        context.context_id,
        query.query_id,
        law.law_id,
        terminal_ref.terminal_ref_id,
    )


@dataclass(frozen=True, slots=True)
class RegisteredExactGroundSemanticAnchorDraftV1:
    semantic_anchor_id: None = None
    anchor_commit_id: None = None
    target_execution_allowed: bool = False
    status: str = "DRAFT_NULL_ANCHOR_NONAUTHORIZING"


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceOperationalTerminalRefDraftV1:
    occurrence_terminal_artifact_id: None = None
    operational_terminal_available: bool = False
    status: str = "MISSING_OPERATIONAL_TERMINAL_NONAUTHORIZING"


def _registered_action(
    value: Any,
    field_name: str,
) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            f"{field_name} must be one exact integer action triple"
        )
    return value


def _require_registered_anchor_without_evaluation_access(
    anchor: Any,
) -> final_authority.V072RemoteMainAnchorV1:
    if (
        type(anchor) is not final_authority.V072RemoteMainAnchorV1
        or final_authority.REMOTE_MAIN_ANCHOR_AUTHORITY_ENABLED is not True
        or anchor.target_execution_allowed is not True
        or type(anchor.claim) is not final_authority.V072RemoteMainAnchorClaimV1
        or anchor.claim.verification_scope
        is not (
            final_authority.RemoteMainAnchorVerificationScopeV1
            .REGISTERED_PRODUCTION_CANDIDATE
        )
    ):
        raise RegisteredIndependentExactGroundEvaluationLocked(
            "registered exact evaluation requires the exact enabled "
            "V072RemoteMainAnchorV1; placeholders, drafts, and duck types "
            "cannot authorize evaluation"
        )
    return anchor


def _require_registered_context_without_evaluation_access(
    context: Any,
) -> registered_prereg.HeldoutPublicGraphContextV2:
    contexts = registered_prereg.registered_heldout_public_contexts_v2()
    if (
        type(context) is not registered_prereg.HeldoutPublicGraphContextV2
        or context not in contexts
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "registered exact evaluation requires one exact preregistered "
            "public context"
        )
    return context


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceIdentityV1:
    """One immutable context-major member of the 3 x 5 schedule."""

    anchor_id: str
    context_id: str
    context_key: str
    arm: str
    context_ordinal: int
    arm_ordinal: int
    occurrence_ordinal: int

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "registered occurrence anchor")
        _cid(self.context_id, "registered occurrence context")
        contexts = registered_prereg.registered_heldout_public_contexts_v2()
        if (
            type(self.context_ordinal) is not int
            or self.context_ordinal not in range(len(contexts))
            or contexts[self.context_ordinal].context_id != self.context_id
            or contexts[self.context_ordinal].context_key != self.context_key
            or type(self.arm) is not str
            or self.arm not in registered_prereg.ARM_ORDER
            or type(self.arm_ordinal) is not int
            or self.arm_ordinal
            != registered_prereg.ARM_ORDER.index(self.arm)
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal
            != (
                self.context_ordinal * len(registered_prereg.ARM_ORDER)
                + self.arm_ordinal
            )
            or self.occurrence_ordinal
            not in range(registered_prereg.CONFIRMATORY_OCCURRENCE_COUNT)
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered exact-ground occurrence is outside the frozen "
                "15-occurrence context-major schedule"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_exact_ground_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "confirmatory_family_generation": (
                registered_prereg.CONFIRMATORY_FAMILY_GENERATION
            ),
            "context_id": self.context_id,
            "context_key": self.context_key,
            "arm": self.arm,
            "context_ordinal": self.context_ordinal,
            "arm_ordinal": self.arm_ordinal,
            "occurrence_ordinal": self.occurrence_ordinal,
            "schedule_context_count": 3,
            "schedule_arm_count": 5,
            "schedule_occurrence_count": 15,
            "replacement_allowed": False,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("registered_occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def registered_occurrence_identity_v1(
    *,
    anchor: Any,
    context: Any,
    arm: str,
) -> RegisteredOccurrenceIdentityV1:
    canonical_anchor = _require_registered_anchor_without_evaluation_access(
        anchor
    )
    canonical_context = (
        _require_registered_context_without_evaluation_access(context)
    )
    if type(arm) is not str or arm not in registered_prereg.ARM_ORDER:
        raise V072IndependentExactGroundEvaluationViolation(
            "registered occurrence arm is outside the frozen five-arm order"
        )
    contexts = registered_prereg.registered_heldout_public_contexts_v2()
    context_ordinal = contexts.index(canonical_context)
    arm_ordinal = registered_prereg.ARM_ORDER.index(arm)
    return RegisteredOccurrenceIdentityV1(
        canonical_anchor.anchor_id,
        canonical_context.context_id,
        canonical_context.context_key,
        arm,
        context_ordinal,
        arm_ordinal,
        context_ordinal * len(registered_prereg.ARM_ORDER) + arm_ordinal,
    )


@dataclass(frozen=True, slots=True)
class RegisteredGroundChildDecisionV1:
    occurrence_id: str
    context_id: str
    state: registered_observer.HeldoutSymbolicGraphStateV2
    action: tuple[int, int, int]

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "registered child-decision occurrence")
        _cid(self.context_id, "registered child-decision context")
        if (
            type(self.state)
            is not registered_observer.HeldoutSymbolicGraphStateV2
            or self.state.failure
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered child decision requires one active exact state"
            )
        _registered_action(self.action, "registered child decision")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_operational_child_decision.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "state": self.state.to_document(),
            "action": list(self.action),
            "remaining_horizon": 1,
        }

    @property
    def decision_id(self) -> str:
        return _content_id(
            "registered_operational_child_decision",
            self._payload(),
        )

    @property
    def semantic_key(self) -> tuple[tuple[int, ...], tuple[int, int, int]]:
        return self.state.ranks, self.action

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


_REGISTERED_OPERATIONAL_TERMINAL_SENTINEL = object()


@dataclass(frozen=True, slots=True)
class RegisteredFixedKappaDecisionV1:
    """One semantic action and its frozen exact ground realization law."""

    _operational_capability: object
    occurrence_id: str
    context_id: str
    ground_state_id: str
    public_state_id: str
    state: registered_observer.HeldoutSymbolicGraphStateV2
    remaining_horizon: int
    semantic_action_id: str
    ground_action_ids: tuple[str, ...]
    ground_semantic_action_ids: tuple[str, ...]
    ground_actions: tuple[tuple[int, int, int], ...]
    uniform_weights: tuple[Fraction, ...]
    source_action_realization_artifact_id: str

    def __post_init__(self) -> None:
        if (
            self._operational_capability
            is not _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL
            or REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is not True
        ):
            raise RegisteredIndependentExactGroundEvaluationLocked(
                REGISTERED_OPERATIONAL_TERMINAL_BLOCKER
            )
        for value, label in (
            (self.occurrence_id, "fixed-kappa occurrence"),
            (self.context_id, "fixed-kappa context"),
            (self.ground_state_id, "fixed-kappa ground state"),
            (self.public_state_id, "fixed-kappa public state"),
            (self.semantic_action_id, "fixed-kappa semantic action"),
            (
                self.source_action_realization_artifact_id,
                "fixed-kappa realization source",
            ),
            *(
                (item, "fixed-kappa ground action")
                for item in self.ground_action_ids
            ),
            *(
                (item, "fixed-kappa ground semantic action")
                for item in self.ground_semantic_action_ids
            ),
        ):
            _cid(value, label)
        if type(self.ground_actions) is tuple:
            for action in self.ground_actions:
                _registered_action(action, "fixed-kappa ground action")
        support_size = len(self.ground_action_ids)
        if (
            type(self.state)
            is not registered_observer.HeldoutSymbolicGraphStateV2
            or self.state.failure
            or self.public_state_id != self.state.state_id
            or self.remaining_horizon not in (1, registered_prereg.HORIZON)
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
            raise V072IndependentExactGroundEvaluationViolation(
                "fixed-kappa support must contain distinct aligned actions "
                "with exact uniform Fraction weights"
            )

    @property
    def singleton(self) -> bool:
        return len(self.ground_actions) == 1

    @property
    def semantic_key(self) -> tuple[tuple[int, ...], int, str]:
        return self.state.ranks, self.remaining_horizon, self.semantic_action_id

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_fixed_kappa_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "ground_state_id": self.ground_state_id,
            "public_state_id": self.public_state_id,
            "state": self.state.to_document(),
            "remaining_horizon": self.remaining_horizon,
            "semantic_action_id": self.semantic_action_id,
            "ground_action_ids": list(self.ground_action_ids),
            "ground_semantic_action_ids": list(
                self.ground_semantic_action_ids
            ),
            "ground_actions": [list(item) for item in self.ground_actions],
            "uniform_weights": [_fdoc(item) for item in self.uniform_weights],
            "source_action_realization_artifact_id": (
                self.source_action_realization_artifact_id
            ),
            "deterministic_semantic_selector": True,
            "fixed_stochastic_concretizer": True,
            "policy_randomization": False,
            "singleton": self.singleton,
        }

    @property
    def decision_id(self) -> str:
        return _content_id("registered_fixed_kappa_decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class RegisteredOperationalSelectedPolicyV1:
    """Caller-proof semantic selector plus frozen κ realization policy."""

    _operational_capability: object
    occurrence: RegisteredOccurrenceIdentityV1
    route_kind: str
    operational_policy_source_artifact_id: str
    independent_runtime_verification_id: str
    root_decision: RegisteredFixedKappaDecisionV1
    child_decisions: tuple[RegisteredFixedKappaDecisionV1, ...]

    def __post_init__(self) -> None:
        if (
            self._operational_capability
            is not _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL
            or REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is not True
            or type(self.occurrence) is not RegisteredOccurrenceIdentityV1
        ):
            raise RegisteredIndependentExactGroundEvaluationLocked(
                REGISTERED_OPERATIONAL_TERMINAL_BLOCKER
            )
        _cid(
            self.operational_policy_source_artifact_id,
            "registered operational policy source",
        )
        _cid(
            self.independent_runtime_verification_id,
            "registered runtime independent verification",
        )
        expected_route = (
            "MATCHED_DIRECT_GROUND"
            if self.occurrence.arm == "MATCHED_DIRECT_GROUND"
            else "ADAPTIVE_QUOTIENT"
        )
        if (
            self.route_kind != expected_route
            or type(self.root_decision) is not RegisteredFixedKappaDecisionV1
            or self.root_decision.occurrence_id
            != self.occurrence.occurrence_id
            or self.root_decision.context_id != self.occurrence.context_id
            or self.root_decision.remaining_horizon
            != registered_prereg.HORIZON
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not RegisteredFixedKappaDecisionV1
                or item.occurrence_id != self.occurrence.occurrence_id
                or item.context_id != self.occurrence.context_id
                or item.remaining_horizon != 1
                for item in self.child_decisions
            )
            or tuple(item.semantic_key for item in self.child_decisions)
            != tuple(
                sorted(
                    {
                        item.semantic_key
                        for item in self.child_decisions
                    }
                )
            )
            or len(
                {
                    item.public_state_id
                    for item in self.child_decisions
                }
            )
            != len(self.child_decisions)
            or (
                self.route_kind == "MATCHED_DIRECT_GROUND"
                and (
                    not self.root_decision.singleton
                    or any(not item.singleton for item in self.child_decisions)
                )
            )
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered fixed-kappa selected policy is malformed, "
                "duplicated, cross-route disguised, or transplanted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_operational_selected_policy.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "context_id": self.occurrence.context_id,
            "arm": self.occurrence.arm,
            "route_kind": self.route_kind,
            "operational_policy_source_artifact_id": (
                self.operational_policy_source_artifact_id
            ),
            "independent_runtime_verification_id": (
                self.independent_runtime_verification_id
            ),
            "root_decision_id": self.root_decision.decision_id,
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "deterministic_semantic_finite_horizon_markov_selector": True,
            "fixed_stochastic_kappa_action_realization": True,
            "policy_randomization": False,
            "caller_supplied_value": False,
            "caller_supplied_risk": False,
            "caller_supplied_status": False,
        }

    @property
    def selected_policy_id(self) -> str:
        return _content_id("registered_operational_policy", self._payload())

    @property
    def semantic_policy_key(self) -> tuple[str, tuple[Any, ...]]:
        return (
            self.root_decision.semantic_action_id,
            tuple(item.semantic_key for item in self.child_decisions),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence": self.occurrence.to_document(),
            "root_decision": self.root_decision.to_document(),
            "child_decisions": [
                item.to_document() for item in self.child_decisions
            ],
            "selected_policy_id": self.selected_policy_id,
        }


_PLAN_TERMINAL_CODES = ("CONDITIONAL_PLAN_CERTIFICATE",)


@dataclass(frozen=True, slots=True)
class RegisteredOccurrenceOperationalTerminalV1:
    _operational_capability: object
    occurrence: RegisteredOccurrenceIdentityV1
    operational_result_artifact_id: str
    selected_policy_id: str
    terminal_code: str

    def __post_init__(self) -> None:
        if (
            self._operational_capability
            is not _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL
            or REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is not True
            or type(self.occurrence) is not RegisteredOccurrenceIdentityV1
        ):
            raise RegisteredIndependentExactGroundEvaluationLocked(
                REGISTERED_OPERATIONAL_TERMINAL_BLOCKER
            )
        _cid(
            self.operational_result_artifact_id,
            "registered operational terminal result",
        )
        _cid(self.selected_policy_id, "registered terminal selected policy")
        if (
            type(self.terminal_code) is not str
            or self.terminal_code not in _PLAN_TERMINAL_CODES
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered exact evaluator accepts only an operational "
                "plan terminal carrying a selected policy"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_occurrence_operational_terminal.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence.occurrence_id,
            "context_id": self.occurrence.context_id,
            "arm": self.occurrence.arm,
            "operational_result_artifact_id": (
                self.operational_result_artifact_id
            ),
            "selected_policy_id": self.selected_policy_id,
            "terminal_code": self.terminal_code,
            "operational_terminal_frozen_before_evaluation": True,
            "evaluation_values_serialized": False,
        }

    @property
    def terminal_id(self) -> str:
        return _content_id("registered_operational_terminal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence": self.occurrence.to_document(),
            "terminal_id": self.terminal_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredOperationalTerminalPolicyBundleV1:
    """Factory output bound to one private verified-runtime authority."""

    mint_authority_id: str
    operational_terminal: RegisteredOccurrenceOperationalTerminalV1
    selected_policy: RegisteredOperationalSelectedPolicyV1

    def __post_init__(self) -> None:
        _cid(self.mint_authority_id, "registered terminal mint authority")
        if (
            type(self.operational_terminal)
            is not RegisteredOccurrenceOperationalTerminalV1
            or type(self.selected_policy)
            is not RegisteredOperationalSelectedPolicyV1
            or self.operational_terminal.occurrence
            != self.selected_policy.occurrence
            or self.operational_terminal.selected_policy_id
            != self.selected_policy.selected_policy_id
            or self.operational_terminal.operational_result_artifact_id
            != (
                self.selected_policy
                .operational_policy_source_artifact_id
            )
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered terminal/policy factory bundle is stale or "
                "transplanted"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_operational_terminal_"
                "policy_bundle.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "mint_authority_id": self.mint_authority_id,
            "occurrence_id": (
                self.operational_terminal.occurrence.occurrence_id
            ),
            "operational_terminal_id": (
                self.operational_terminal.terminal_id
            ),
            "selected_policy_id": self.selected_policy.selected_policy_id,
            "terminal_and_policy_caller_supplied": False,
        }

    @property
    def bundle_id(self) -> str:
        return _content_id(
            "registered_operational_terminal_policy_bundle",
            self._payload(),
        )

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "operational_terminal": self.operational_terminal.to_document(),
            "selected_policy": self.selected_policy.to_document(),
            "bundle_id": self.bundle_id,
        }


def mint_registered_occurrence_operational_terminal_policy_v1(
    *,
    mint_authority: RegisteredEvaluatorTerminalMintAuthorityV1,
) -> RegisteredOperationalTerminalPolicyBundleV1:
    """Mint only from the private independently verified-runtime authority."""

    from . import v072_registered_operational_terminal_authority_v1 as authority

    canonical = authority.consume_evaluator_terminal_mint_authority_v1(
        mint_authority
    )

    def mint_decision(spec: Any) -> RegisteredFixedKappaDecisionV1:
        state = registered_observer.HeldoutSymbolicGraphStateV2(
            spec.state_ranks
        )
        return RegisteredFixedKappaDecisionV1(
            _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL,
            canonical.occurrence.occurrence_id,
            canonical.occurrence.context_id,
            spec.ground_state_id,
            spec.public_state_id,
            state,
            spec.remaining_horizon,
            spec.semantic_action_id,
            spec.ground_action_ids,
            spec.ground_semantic_action_ids,
            spec.ground_actions,
            spec.uniform_weights,
            spec.source_action_realization_artifact_id,
        )

    root_decision = mint_decision(canonical.root_decision)
    child_decisions = tuple(
        sorted(
            (mint_decision(item) for item in canonical.child_decisions),
            key=lambda item: item.semantic_key,
        )
    )
    selected_policy = RegisteredOperationalSelectedPolicyV1(
        _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL,
        canonical.occurrence,
        canonical.route_kind.value,
        canonical.operational_result_artifact_id,
        canonical.independent_runtime_verification_id,
        root_decision,
        child_decisions,
    )
    terminal = RegisteredOccurrenceOperationalTerminalV1(
        _REGISTERED_OPERATIONAL_TERMINAL_SENTINEL,
        canonical.occurrence,
        canonical.operational_result_artifact_id,
        selected_policy.selected_policy_id,
        canonical.terminal_code,
    )
    return RegisteredOperationalTerminalPolicyBundleV1(
        canonical.mint_authority_id,
        terminal,
        selected_policy,
    )


@dataclass(frozen=True, slots=True)
class RegisteredExactGroundRowV1:
    anchor_id: str
    environment_manifest_id: str
    occurrence_id: str
    context_id: str
    catalogue: registered_observer.HeldoutLegalActionCatalogueV2
    action: tuple[int, int, int]
    atoms: tuple[registered_observer.EvaluationOnlyExactAtomV2, ...]

    def __post_init__(self) -> None:
        for value, field_name in (
            (self.anchor_id, "registered exact row anchor"),
            (
                self.environment_manifest_id,
                "registered exact row environment",
            ),
            (self.occurrence_id, "registered exact row occurrence"),
            (self.context_id, "registered exact row context"),
        ):
            _cid(value, field_name)
        if (
            type(self.catalogue)
            is not registered_observer.HeldoutLegalActionCatalogueV2
            or self.catalogue.context_id != self.context_id
            or _registered_action(self.action, "registered exact row")
            not in self.catalogue.actions
            or type(self.atoms) is not tuple
            or not self.atoms
            or any(
                type(item)
                is not registered_observer.EvaluationOnlyExactAtomV2
                or item.anchor_id != self.anchor_id
                or item.environment_manifest_id
                != self.environment_manifest_id
                or item.context_id != self.context_id
                or item.catalogue_id != self.catalogue.catalogue_id
                or item.action != self.action
                or item.execution_lane != "EVALUATION_ONLY"
                or item.terminal
                != (
                    item.failure
                    or self.catalogue.remaining_horizon == 1
                )
                for item in self.atoms
            )
            or tuple(item.atom_id for item in self.atoms)
            != tuple(sorted({item.atom_id for item in self.atoms}))
            or sum(
                (item.probability for item in self.atoms),
                Fraction(0),
            )
            != 1
            or len(
                {item.realized_row_reward for item in self.atoms}
            )
            != 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered exact-ground row is incomplete or noncanonical"
            )

    @property
    def reward(self) -> Fraction:
        return self.atoms[0].realized_row_reward

    @property
    def failure_probability(self) -> Fraction:
        return sum(
            (
                atom.probability
                for atom in self.atoms
                if atom.failure
            ),
            Fraction(0),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v072_registered_exact_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "anchor_id": self.anchor_id,
            "environment_manifest_id": self.environment_manifest_id,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "state_id": self.catalogue.state.state_id,
            "remaining_horizon": self.catalogue.remaining_horizon,
            "action": list(self.action),
            "atom_ids": [item.atom_id for item in self.atoms],
            "reward": _fdoc(self.reward),
            "failure_probability": _fdoc(self.failure_probability),
            "execution_lane": EVALUATION_LANE,
        }

    @property
    def row_id(self) -> str:
        return _content_id("registered_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogue": self.catalogue.to_document(),
            "atoms": [item.to_document() for item in self.atoms],
            "row_id": self.row_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredExactGroundPolicyWitnessV1:
    occurrence_id: str
    context_id: str
    root_action: tuple[int, int, int]
    child_decisions: tuple[RegisteredGroundChildDecisionV1, ...]
    expected_reward: Fraction
    failure_probability: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "registered policy-witness occurrence")
        _cid(self.context_id, "registered policy-witness context")
        _registered_action(self.root_action, "registered policy-witness root")
        if (
            type(self.child_decisions) is not tuple
            or any(
                type(item) is not RegisteredGroundChildDecisionV1
                or item.occurrence_id != self.occurrence_id
                or item.context_id != self.context_id
                for item in self.child_decisions
            )
            or tuple(item.semantic_key for item in self.child_decisions)
            != tuple(
                sorted(
                    {
                        item.semantic_key
                        for item in self.child_decisions
                    }
                )
            )
            or type(self.expected_reward) is not Fraction
            or self.expected_reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered exact-ground policy witness is malformed"
            )

    @property
    def semantic_policy_key(
        self,
    ) -> tuple[
        tuple[int, int, int],
        tuple[tuple[tuple[int, ...], tuple[int, int, int]], ...],
    ]:
        return (
            self.root_action,
            tuple(item.semantic_key for item in self.child_decisions),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_exact_ground_policy_witness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "root_action": list(self.root_action),
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "expected_reward": _fdoc(self.expected_reward),
            "failure_probability": _fdoc(self.failure_probability),
            "deterministic": True,
        }

    @property
    def policy_witness_id(self) -> str:
        return _content_id("registered_policy_witness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "child_decisions": [
                item.to_document() for item in self.child_decisions
            ],
            "policy_witness_id": self.policy_witness_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredFixedKappaPolicyWitnessV1:
    """Exact value of a deterministic selector with frozen κ realization."""

    occurrence_id: str
    context_id: str
    route_kind: str
    root_decision: RegisteredFixedKappaDecisionV1
    child_decisions: tuple[RegisteredFixedKappaDecisionV1, ...]
    expected_reward: Fraction
    failure_probability: Fraction

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "fixed-kappa witness occurrence")
        _cid(self.context_id, "fixed-kappa witness context")
        if (
            self.route_kind
            not in ("ADAPTIVE_QUOTIENT", "MATCHED_DIRECT_GROUND")
            or type(self.root_decision) is not RegisteredFixedKappaDecisionV1
            or self.root_decision.occurrence_id != self.occurrence_id
            or self.root_decision.context_id != self.context_id
            or self.root_decision.remaining_horizon
            != registered_prereg.HORIZON
            or type(self.child_decisions) is not tuple
            or any(
                type(item) is not RegisteredFixedKappaDecisionV1
                or item.occurrence_id != self.occurrence_id
                or item.context_id != self.context_id
                or item.remaining_horizon != 1
                for item in self.child_decisions
            )
            or tuple(item.semantic_key for item in self.child_decisions)
            != tuple(sorted({item.semantic_key for item in self.child_decisions}))
            or type(self.expected_reward) is not Fraction
            or self.expected_reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered fixed-kappa policy witness is malformed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_fixed_kappa_policy_witness.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "route_kind": self.route_kind,
            "root_decision_id": self.root_decision.decision_id,
            "child_decision_ids": [
                item.decision_id for item in self.child_decisions
            ],
            "expected_reward": _fdoc(self.expected_reward),
            "failure_probability": _fdoc(self.failure_probability),
            "deterministic_semantic_selector": True,
            "fixed_stochastic_kappa_action_realization": True,
            "policy_randomization": False,
        }

    @property
    def policy_witness_id(self) -> str:
        return _content_id("registered_kappa_policy_witness", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "root_decision": self.root_decision.to_document(),
            "child_decisions": [
                item.to_document() for item in self.child_decisions
            ],
            "policy_witness_id": self.policy_witness_id,
        }


@dataclass(frozen=True, slots=True)
class RegisteredExactGroundEvaluationWorkV1:
    evaluation_exact_atom_api_calls: int
    exact_rows_reconstructed: int
    exact_atoms_reconstructed: int
    dp_candidate_extensions: int
    dp_dominance_comparisons: int
    dp_frontier_points_retained: int
    selected_policy_assignments_checked: int
    operational_work_records_written: int = 0
    accepted_sample_draws: int = 0
    source_prior_reads: int = 0
    execution_lane: str = EVALUATION_LANE

    def __post_init__(self) -> None:
        values = tuple(
            getattr(self, name)
            for name in self.__dataclass_fields__
            if name != "execution_lane"
        )
        if (
            any(type(value) is not int or value < 0 for value in values)
            or self.evaluation_exact_atom_api_calls <= 0
            or self.exact_rows_reconstructed
            != self.evaluation_exact_atom_api_calls
            or self.exact_atoms_reconstructed
            < self.exact_rows_reconstructed
            or self.dp_candidate_extensions <= 0
            or self.dp_frontier_points_retained <= 0
            or self.selected_policy_assignments_checked <= 0
            or any(value != 0 for value in values[-3:])
            or self.execution_lane != EVALUATION_LANE
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered evaluation-only work does not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_exact_ground_evaluation_work.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            **{
                name: getattr(self, name)
                for name in self.__dataclass_fields__
            },
        }

    @property
    def work_id(self) -> str:
        return _content_id("registered_work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


class RegisteredExactGroundEvaluationStatusV1(str, Enum):
    CERTIFICATE_METRICS_PASS = "CERTIFICATE_METRICS_PASS"
    SELECTED_POLICY_RISK_VIOLATION = "SELECTED_POLICY_RISK_VIOLATION"
    SELECTED_POLICY_REGRET_VIOLATION = "SELECTED_POLICY_REGRET_VIOLATION"
    GROUND_QUERY_INFEASIBLE = "GROUND_QUERY_INFEASIBLE"


@dataclass(frozen=True, slots=True)
class RegisteredIndependentExactGroundEvaluationResultV1:
    anchor_id: str
    occurrence: RegisteredOccurrenceIdentityV1
    operational_terminal_id: str
    operational_selected_policy_id: str
    status: RegisteredExactGroundEvaluationStatusV1
    rows: tuple[RegisteredExactGroundRowV1, ...]
    optimal_policy: RegisteredExactGroundPolicyWitnessV1 | None
    selected_policy: RegisteredFixedKappaPolicyWitnessV1
    optimal_expected_reward: Fraction | None
    optimal_failure_probability: Fraction | None
    selected_expected_reward: Fraction
    selected_failure_probability: Fraction
    regret: Fraction | None
    normalized_regret: Fraction | None
    risk_pass: bool
    regret_pass: bool
    certificate_metrics_pass: bool
    work: RegisteredExactGroundEvaluationWorkV1
    execution_lane: str = EVALUATION_LANE
    operational_work_included: bool = False

    def __post_init__(self) -> None:
        _cid(self.anchor_id, "registered exact result anchor")
        _cid(
            self.operational_terminal_id,
            "registered exact result terminal",
        )
        _cid(
            self.operational_selected_policy_id,
            "registered exact result selected policy",
        )
        if (
            type(self.occurrence) is not RegisteredOccurrenceIdentityV1
            or self.occurrence.anchor_id != self.anchor_id
            or type(self.status)
            is not RegisteredExactGroundEvaluationStatusV1
            or type(self.rows) is not tuple
            or not self.rows
            or any(
                type(row) is not RegisteredExactGroundRowV1
                or row.anchor_id != self.anchor_id
                or row.occurrence_id != self.occurrence.occurrence_id
                or row.context_id != self.occurrence.context_id
                for row in self.rows
            )
            or tuple(row.row_id for row in self.rows)
            != tuple(sorted({row.row_id for row in self.rows}))
            or (
                self.optimal_policy is not None
                and (
                    type(self.optimal_policy)
                    is not RegisteredExactGroundPolicyWitnessV1
                    or self.optimal_policy.occurrence_id
                    != self.occurrence.occurrence_id
                )
            )
            or type(self.selected_policy)
            is not RegisteredFixedKappaPolicyWitnessV1
            or self.selected_policy.occurrence_id
            != self.occurrence.occurrence_id
            or type(self.selected_expected_reward) is not Fraction
            or type(self.selected_failure_probability) is not Fraction
            or type(self.risk_pass) is not bool
            or type(self.regret_pass) is not bool
            or type(self.certificate_metrics_pass) is not bool
            or type(self.work)
            is not RegisteredExactGroundEvaluationWorkV1
            or self.execution_lane != EVALUATION_LANE
            or self.operational_work_included is not False
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered independent exact-ground result is malformed"
            )
        if (
            self.selected_policy.expected_reward
            != self.selected_expected_reward
            or self.selected_policy.failure_probability
            != self.selected_failure_probability
            or self.risk_pass
            != (
                self.selected_failure_probability
                <= registered_prereg.RISK_TOLERANCE
            )
            or self.certificate_metrics_pass
            != (self.risk_pass and self.regret_pass)
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered selected-policy metric summary is stale"
            )
        if self.optimal_policy is None:
            if (
                self.status
                is not (
                    RegisteredExactGroundEvaluationStatusV1
                    .GROUND_QUERY_INFEASIBLE
                )
                or self.optimal_expected_reward is not None
                or self.optimal_failure_probability is not None
                or self.regret is not None
                or self.normalized_regret is not None
                or self.regret_pass
                or self.certificate_metrics_pass
            ):
                raise V072IndependentExactGroundEvaluationViolation(
                    "ground-infeasible result carries feasible metrics"
                )
        else:
            if (
                self.optimal_expected_reward
                != self.optimal_policy.expected_reward
                or self.optimal_failure_probability
                != self.optimal_policy.failure_probability
            ):
                raise V072IndependentExactGroundEvaluationViolation(
                    "registered ground optimum summary is stale"
                )
            if self.risk_pass:
                expected_regret = (
                    self.optimal_expected_reward
                    - self.selected_expected_reward
                )
                if (
                    self.regret != expected_regret
                    or self.normalized_regret
                    != expected_regret / registered_prereg.REWARD_CEILING
                    or self.regret_pass
                    != (
                        self.normalized_regret
                        <= (
                            registered_prereg
                            .NORMALIZED_REGRET_TOLERANCE
                        )
                    )
                ):
                    raise V072IndependentExactGroundEvaluationViolation(
                        "registered exact regret computation is stale"
                    )
            elif (
                self.regret is not None
                or self.normalized_regret is not None
                or self.regret_pass
            ):
                raise V072IndependentExactGroundEvaluationViolation(
                    "infeasible selected policy cannot claim regret pass"
                )
        expected_status = (
            RegisteredExactGroundEvaluationStatusV1.GROUND_QUERY_INFEASIBLE
            if self.optimal_policy is None
            else (
                RegisteredExactGroundEvaluationStatusV1
                .SELECTED_POLICY_RISK_VIOLATION
                if not self.risk_pass
                else (
                    RegisteredExactGroundEvaluationStatusV1
                    .SELECTED_POLICY_REGRET_VIOLATION
                    if not self.regret_pass
                    else (
                        RegisteredExactGroundEvaluationStatusV1
                        .CERTIFICATE_METRICS_PASS
                    )
                )
            )
        )
        if self.status is not expected_status:
            raise V072IndependentExactGroundEvaluationViolation(
                "registered exact result status was caller-selected or stale"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v072_registered_independent_exact_ground_result.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_id": self.anchor_id,
            "occurrence_id": self.occurrence.occurrence_id,
            "operational_terminal_id": self.operational_terminal_id,
            "operational_selected_policy_id": (
                self.operational_selected_policy_id
            ),
            "status": self.status.value,
            "row_ids": [row.row_id for row in self.rows],
            "optimal_policy_witness_id": (
                None
                if self.optimal_policy is None
                else self.optimal_policy.policy_witness_id
            ),
            "selected_policy_witness_id": (
                self.selected_policy.policy_witness_id
            ),
            "optimal_expected_reward": (
                None
                if self.optimal_expected_reward is None
                else _fdoc(self.optimal_expected_reward)
            ),
            "optimal_failure_probability": (
                None
                if self.optimal_failure_probability is None
                else _fdoc(self.optimal_failure_probability)
            ),
            "selected_expected_reward": _fdoc(
                self.selected_expected_reward
            ),
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "regret": None if self.regret is None else _fdoc(self.regret),
            "normalized_regret": (
                None
                if self.normalized_regret is None
                else _fdoc(self.normalized_regret)
            ),
            "risk_pass": self.risk_pass,
            "regret_pass": self.regret_pass,
            "certificate_metrics_pass": self.certificate_metrics_pass,
            "work_id": self.work.work_id,
            "execution_lane": EVALUATION_LANE,
            "operational_work_included": False,
            "caller_hidden_law_accepted": False,
            "caller_probabilities_accepted": False,
            "caller_status_accepted": False,
            "caller_counts_accepted": False,
            "exact_atom_authority": (
                "heldout_graph_transition_observer_v2."
                "evaluation_only_exact_atoms_v2"
            ),
        }

    @property
    def result_id(self) -> str:
        return _content_id("registered_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "occurrence": self.occurrence.to_document(),
            "rows": [row.to_document() for row in self.rows],
            "optimal_policy": (
                None
                if self.optimal_policy is None
                else self.optimal_policy.to_document()
            ),
            "selected_policy": self.selected_policy.to_document(),
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }


@dataclass(frozen=True, slots=True)
class GenericH2ChildActionV1:
    action: tuple[int, int, int]
    reward: Fraction
    failure_probability: Fraction

    def __post_init__(self) -> None:
        _registered_action(self.action, "generic H=2 child action")
        if (
            type(self.reward) is not Fraction
            or self.reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 child action metrics are malformed"
            )


@dataclass(frozen=True, slots=True)
class GenericH2ChildBranchV1:
    state_key: tuple[int, ...]
    probability: Fraction
    actions: tuple[GenericH2ChildActionV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.state_key) is not tuple
            or not self.state_key
            or any(type(item) is not int for item in self.state_key)
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.actions) is not tuple
            or not self.actions
            or any(
                type(item) is not GenericH2ChildActionV1
                for item in self.actions
            )
            or tuple(item.action for item in self.actions)
            != tuple(sorted({item.action for item in self.actions}))
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 child branch is malformed"
            )


@dataclass(frozen=True, slots=True)
class GenericH2RootActionV1:
    action: tuple[int, int, int]
    reward: Fraction
    immediate_failure_probability: Fraction
    child_branches: tuple[GenericH2ChildBranchV1, ...]

    def __post_init__(self) -> None:
        _registered_action(self.action, "generic H=2 root action")
        if (
            type(self.reward) is not Fraction
            or self.reward < 0
            or type(self.immediate_failure_probability) is not Fraction
            or not 0 <= self.immediate_failure_probability <= 1
            or type(self.child_branches) is not tuple
            or any(
                type(item) is not GenericH2ChildBranchV1
                for item in self.child_branches
            )
            or tuple(item.state_key for item in self.child_branches)
            != tuple(
                sorted(
                    {
                        item.state_key
                        for item in self.child_branches
                    }
                )
            )
            or (
                self.immediate_failure_probability
                + sum(
                    (
                        item.probability
                        for item in self.child_branches
                    ),
                    Fraction(0),
                )
                != 1
            )
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 root action is malformed or unnormalized"
            )


@dataclass(frozen=True, slots=True)
class GenericH2DeterministicPolicyV1:
    root_action: tuple[int, int, int]
    child_actions: tuple[
        tuple[tuple[int, ...], tuple[int, int, int]],
        ...,
    ]
    expected_reward: Fraction
    failure_probability: Fraction

    def __post_init__(self) -> None:
        _registered_action(self.root_action, "generic H=2 policy root")
        if (
            type(self.child_actions) is not tuple
            or self.child_actions
            != tuple(sorted(set(self.child_actions)))
            or any(
                type(state_key) is not tuple
                or not state_key
                or any(type(item) is not int for item in state_key)
                or _registered_action(
                    action,
                    "generic H=2 policy child",
                )
                != action
                for state_key, action in self.child_actions
            )
            or type(self.expected_reward) is not Fraction
            or self.expected_reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 deterministic policy is malformed"
            )

    @property
    def semantic_key(
        self,
    ) -> tuple[
        tuple[int, int, int],
        tuple[
            tuple[tuple[int, ...], tuple[int, int, int]],
            ...,
        ],
    ]:
        return self.root_action, self.child_actions


@dataclass(frozen=True, slots=True)
class GenericH2UniformKappaDecisionV1:
    semantic_action_id: str
    actions: tuple[tuple[int, int, int], ...]
    uniform_weights: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        if type(self.actions) is tuple:
            for action in self.actions:
                _registered_action(action, "generic fixed-kappa action")
        support_size = len(self.actions)
        if (
            type(self.semantic_action_id) is not str
            or not self.semantic_action_id
            or type(self.actions) is not tuple
            or self.actions != tuple(sorted(set(self.actions)))
            or support_size == 0
            or type(self.uniform_weights) is not tuple
            or self.uniform_weights
            != tuple(Fraction(1, support_size) for _ in range(support_size))
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic fixed-kappa decision requires distinct actions and "
                "exact uniform Fraction weights"
            )


@dataclass(frozen=True, slots=True)
class GenericH2FixedKappaPolicyV1:
    root_decision: GenericH2UniformKappaDecisionV1
    child_decisions: tuple[
        tuple[tuple[int, ...], GenericH2UniformKappaDecisionV1],
        ...,
    ]
    expected_reward: Fraction
    failure_probability: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.root_decision)
            is not GenericH2UniformKappaDecisionV1
            or type(self.child_decisions) is not tuple
            or self.child_decisions
            != tuple(sorted(self.child_decisions, key=lambda item: item[0]))
            or len({item[0] for item in self.child_decisions})
            != len(self.child_decisions)
            or any(
                type(state_key) is not tuple
                or not state_key
                or type(decision) is not GenericH2UniformKappaDecisionV1
                for state_key, decision in self.child_decisions
            )
            or type(self.expected_reward) is not Fraction
            or self.expected_reward < 0
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 fixed-kappa policy is malformed"
            )


@dataclass(frozen=True, slots=True)
class GenericH2DeterministicCoreResultV1:
    policies: tuple[GenericH2DeterministicPolicyV1, ...]
    optimal_policy: GenericH2DeterministicPolicyV1 | None
    risk_tolerance: Fraction
    candidate_extensions: int
    dominance_comparisons: int
    frontier_points_retained: int

    def __post_init__(self) -> None:
        if (
            type(self.policies) is not tuple
            or not self.policies
            or any(
                type(item) is not GenericH2DeterministicPolicyV1
                for item in self.policies
            )
            or type(self.risk_tolerance) is not Fraction
            or not 0 <= self.risk_tolerance <= 1
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.candidate_extensions,
                    self.dominance_comparisons,
                    self.frontier_points_retained,
                )
            )
            or self.candidate_extensions <= 0
            or self.frontier_points_retained <= 0
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 deterministic core result is malformed"
            )
        feasible = tuple(
            item
            for item in self.policies
            if item.failure_probability <= self.risk_tolerance
        )
        expected = (
            min(
                feasible,
                key=lambda item: (
                    -item.expected_reward,
                    item.failure_probability,
                    item.semantic_key,
                ),
            )
            if feasible
            else None
        )
        if self.optimal_policy != expected:
            raise V072IndependentExactGroundEvaluationViolation(
                "generic H=2 deterministic optimum is stale"
            )


@dataclass(frozen=True, slots=True)
class _GenericH2FrontierPoint:
    expected_reward: Fraction
    failure_probability: Fraction
    child_actions: tuple[
        tuple[tuple[int, ...], tuple[int, int, int]],
        ...,
    ]

    @property
    def semantic_key(
        self,
    ) -> tuple[tuple[tuple[int, ...], tuple[int, int, int]], ...]:
        return self.child_actions


def _prune_generic_h2_frontier(
    points: tuple[_GenericH2FrontierPoint, ...],
) -> tuple[tuple[_GenericH2FrontierPoint, ...], int]:
    by_value: dict[
        tuple[Fraction, Fraction],
        _GenericH2FrontierPoint,
    ] = {}
    for point in points:
        key = point.expected_reward, point.failure_probability
        current = by_value.get(key)
        if current is None or point.semantic_key < current.semantic_key:
            by_value[key] = point
    unique = tuple(by_value.values())
    retained: list[_GenericH2FrontierPoint] = []
    comparisons = 0
    for candidate in unique:
        dominated = False
        for challenger in unique:
            if challenger is candidate:
                continue
            comparisons += 1
            if (
                challenger.failure_probability
                <= candidate.failure_probability
                and challenger.expected_reward
                >= candidate.expected_reward
                and (
                    challenger.failure_probability
                    < candidate.failure_probability
                    or challenger.expected_reward
                    > candidate.expected_reward
                )
            ):
                dominated = True
                break
        if not dominated:
            retained.append(candidate)
    return (
        tuple(
            sorted(
                retained,
                key=lambda item: (
                    item.failure_probability,
                    -item.expected_reward,
                    item.semantic_key,
                ),
            )
        ),
        comparisons,
    )


def solve_generic_h2_deterministic_core_v1(
    *,
    root_actions: tuple[GenericH2RootActionV1, ...],
    risk_tolerance: Fraction,
) -> GenericH2DeterministicCoreResultV1:
    """Exact Pareto DP with no domain, observer, model, or policy authority."""

    if (
        type(root_actions) is not tuple
        or not root_actions
        or any(type(item) is not GenericH2RootActionV1 for item in root_actions)
        or tuple(item.action for item in root_actions)
        != tuple(sorted({item.action for item in root_actions}))
        or type(risk_tolerance) is not Fraction
        or not 0 <= risk_tolerance <= 1
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "generic H=2 deterministic core input is malformed"
        )
    policies: list[GenericH2DeterministicPolicyV1] = []
    candidate_extensions = 0
    dominance_comparisons = 0
    frontier_points_retained = 0
    for root in root_actions:
        frontier = (
            _GenericH2FrontierPoint(
                root.reward,
                root.immediate_failure_probability,
                (),
            ),
        )
        for branch in root.child_branches:
            candidates: list[_GenericH2FrontierPoint] = []
            for point in frontier:
                for child in branch.actions:
                    candidates.append(
                        _GenericH2FrontierPoint(
                            point.expected_reward
                            + branch.probability * child.reward,
                            point.failure_probability
                            + branch.probability
                            * child.failure_probability,
                            tuple(
                                sorted(
                                    (
                                        *point.child_actions,
                                        (branch.state_key, child.action),
                                    )
                                )
                            ),
                        )
                    )
                    candidate_extensions += 1
            frontier, comparisons = _prune_generic_h2_frontier(
                tuple(candidates)
            )
            dominance_comparisons += comparisons
            frontier_points_retained += len(frontier)
        policies.extend(
            GenericH2DeterministicPolicyV1(
                root.action,
                point.child_actions,
                point.expected_reward,
                point.failure_probability,
            )
            for point in frontier
        )
    policy_tuple = tuple(
        sorted(
            policies,
            key=lambda item: (
                item.failure_probability,
                -item.expected_reward,
                item.semantic_key,
            ),
        )
    )
    feasible = tuple(
        item
        for item in policy_tuple
        if item.failure_probability <= risk_tolerance
    )
    optimal = (
        min(
            feasible,
            key=lambda item: (
                -item.expected_reward,
                item.failure_probability,
                item.semantic_key,
            ),
        )
        if feasible
        else None
    )
    return GenericH2DeterministicCoreResultV1(
        policy_tuple,
        optimal,
        risk_tolerance,
        candidate_extensions,
        dominance_comparisons,
        frontier_points_retained,
    )


def evaluate_generic_h2_deterministic_policy_v1(
    *,
    root_actions: tuple[GenericH2RootActionV1, ...],
    root_action: tuple[int, int, int],
    child_actions: tuple[
        tuple[tuple[int, ...], tuple[int, int, int]],
        ...,
    ],
) -> GenericH2DeterministicPolicyV1:
    """Evaluate one complete deterministic policy against frozen row metrics."""

    if (
        type(root_actions) is not tuple
        or any(type(item) is not GenericH2RootActionV1 for item in root_actions)
        or _registered_action(root_action, "generic selected root")
        != root_action
        or type(child_actions) is not tuple
        or child_actions != tuple(sorted(set(child_actions)))
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "generic selected H=2 policy is malformed"
        )
    roots = tuple(item for item in root_actions if item.action == root_action)
    if len(roots) != 1:
        raise V072IndependentExactGroundEvaluationViolation(
            "generic selected root action is absent or duplicated"
        )
    root = roots[0]
    assignment = dict(child_actions)
    if set(assignment) != {
        branch.state_key for branch in root.child_branches
    }:
        raise V072IndependentExactGroundEvaluationViolation(
            "generic selected policy does not cover exactly its child states"
        )
    reward = root.reward
    risk = root.immediate_failure_probability
    for branch in root.child_branches:
        action = assignment[branch.state_key]
        options = tuple(
            item for item in branch.actions if item.action == action
        )
        if len(options) != 1:
            raise V072IndependentExactGroundEvaluationViolation(
                "generic selected child action is absent or duplicated"
            )
        reward += branch.probability * options[0].reward
        risk += (
            branch.probability * options[0].failure_probability
        )
    return GenericH2DeterministicPolicyV1(
        root_action,
        child_actions,
        reward,
        risk,
    )


def evaluate_generic_h2_fixed_kappa_policy_v1(
    *,
    root_actions: tuple[GenericH2RootActionV1, ...],
    root_decision: GenericH2UniformKappaDecisionV1,
    child_decisions: tuple[
        tuple[tuple[int, ...], GenericH2UniformKappaDecisionV1],
        ...,
    ],
) -> GenericH2FixedKappaPolicyV1:
    """Evaluate frozen κ exactly; never select one representative action."""

    if (
        type(root_actions) is not tuple
        or any(type(item) is not GenericH2RootActionV1 for item in root_actions)
        or type(root_decision) is not GenericH2UniformKappaDecisionV1
        or type(child_decisions) is not tuple
        or child_decisions
        != tuple(sorted(child_decisions, key=lambda item: item[0]))
        or len({item[0] for item in child_decisions}) != len(child_decisions)
        or any(
            type(state_key) is not tuple
            or type(decision) is not GenericH2UniformKappaDecisionV1
            for state_key, decision in child_decisions
        )
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "generic fixed-kappa H=2 policy is malformed"
        )
    root_by_action = {item.action: item for item in root_actions}
    if len(root_by_action) != len(root_actions):
        raise V072IndependentExactGroundEvaluationViolation(
            "generic fixed-kappa exact root inventory is duplicated"
        )
    selected_roots = tuple(
        (weight, root_by_action.get(action))
        for action, weight in zip(
            root_decision.actions,
            root_decision.uniform_weights,
            strict=True,
        )
    )
    if any(item is None for _, item in selected_roots):
        raise V072IndependentExactGroundEvaluationViolation(
            "generic fixed-kappa root support is outside exact inventory"
        )
    canonical_roots = tuple(
        (weight, item) for weight, item in selected_roots if item is not None
    )
    child_by_state = dict(child_decisions)
    required_states = {
        branch.state_key
        for _, root in canonical_roots
        for branch in root.child_branches
    }
    if set(child_by_state) != required_states:
        raise V072IndependentExactGroundEvaluationViolation(
            "generic fixed-kappa policy does not cover exactly the reachable "
            "child-state union"
        )
    reward = Fraction(0)
    risk = Fraction(0)
    for root_weight, root in canonical_roots:
        conditional_reward = root.reward
        conditional_risk = root.immediate_failure_probability
        for branch in root.child_branches:
            decision = child_by_state[branch.state_key]
            options = {item.action: item for item in branch.actions}
            child_reward = Fraction(0)
            child_risk = Fraction(0)
            for action, weight in zip(
                decision.actions,
                decision.uniform_weights,
                strict=True,
            ):
                option = options.get(action)
                if option is None:
                    raise V072IndependentExactGroundEvaluationViolation(
                        "generic fixed-kappa child support is outside exact "
                        "inventory"
                    )
                child_reward += weight * option.reward
                child_risk += weight * option.failure_probability
            conditional_reward += branch.probability * child_reward
            conditional_risk += branch.probability * child_risk
        reward += root_weight * conditional_reward
        risk += root_weight * conditional_risk
    return GenericH2FixedKappaPolicyV1(
        root_decision,
        child_decisions,
        reward,
        risk,
    )


def evaluate_development_h2_generic_dp_control_v1(
    *,
    anchor: Any,
    context: Any,
    query: Any,
    law: Any,
    terminal_ref: Any,
) -> GenericH2DeterministicCoreResultV1:
    """Exercise the shared DP only on disjoint K4/K5 development laws."""

    (
        _canonical_anchor,
        canonical_context,
        canonical_query,
        canonical_law,
        _canonical_terminal,
    ) = _validate_development_bindings(
        anchor=anchor,
        context=context,
        query=query,
        law=law,
        terminal_ref=terminal_ref,
    )
    row_cache: dict[
        tuple[tuple[int, ...], int, tuple[int, int, int]],
        ExactGroundRowV1,
    ] = {}

    def row_for(
        ranks: tuple[int, ...],
        remaining_horizon: int,
        action: tuple[int, int, int],
    ) -> ExactGroundRowV1:
        key = ranks, remaining_horizon, action
        if key not in row_cache:
            row_cache[key] = _enumerate_row(
                context=canonical_context,
                query=canonical_query,
                law=canonical_law,
                ranks=ranks,
                remaining_horizon=remaining_horizon,
                action=action,
            )
        return row_cache[key]

    root_specs: list[GenericH2RootActionV1] = []
    for root_action in _legal_actions(
        canonical_context,
        canonical_query.root_ranks,
    ):
        root_row = row_for(
            canonical_query.root_ranks,
            HORIZON,
            root_action,
        )
        active_probabilities: dict[tuple[int, ...], Fraction] = {}
        immediate_failure = Fraction(0)
        for transition in root_row.transitions:
            if transition.failure:
                immediate_failure += transition.probability
            elif not transition.terminal:
                active_probabilities[transition.next_ranks] = (
                    active_probabilities.get(
                        transition.next_ranks,
                        Fraction(0),
                    )
                    + transition.probability
                )
        child_specs = []
        for ranks, probability in sorted(active_probabilities.items()):
            child_specs.append(
                GenericH2ChildBranchV1(
                    ranks,
                    probability,
                    tuple(
                        GenericH2ChildActionV1(
                            action,
                            row_for(ranks, 1, action).reward,
                            row_for(
                                ranks,
                                1,
                                action,
                            ).failure_probability,
                        )
                        for action in _legal_actions(
                            canonical_context,
                            ranks,
                        )
                    ),
                )
            )
        root_specs.append(
            GenericH2RootActionV1(
                root_action,
                root_row.reward,
                immediate_failure,
                tuple(child_specs),
            )
        )
    return solve_generic_h2_deterministic_core_v1(
        root_actions=tuple(root_specs),
        risk_tolerance=canonical_query.risk_tolerance,
    )


def _validate_registered_evaluation_inputs(
    *,
    anchor: Any,
    context: Any,
    operational_terminal: Any,
    selected_policy: Any,
) -> tuple[
    final_authority.V072RemoteMainAnchorV1,
    registered_prereg.HeldoutPublicGraphContextV2,
    RegisteredOccurrenceOperationalTerminalV1,
    RegisteredOperationalSelectedPolicyV1,
]:
    canonical_anchor = _require_registered_anchor_without_evaluation_access(
        anchor
    )
    canonical_context = (
        _require_registered_context_without_evaluation_access(context)
    )
    if REGISTERED_EVALUATION_ALLOWED is not True:
        raise RegisteredIndependentExactGroundEvaluationLocked(
            "registered exact evaluation remains disabled until the "
            "operational terminal authority is integrated"
        )
    if (
        REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED is not True
        or type(operational_terminal)
        is not RegisteredOccurrenceOperationalTerminalV1
        or type(selected_policy)
        is not RegisteredOperationalSelectedPolicyV1
    ):
        raise RegisteredIndependentExactGroundEvaluationLocked(
            REGISTERED_OPERATIONAL_TERMINAL_BLOCKER
        )
    expected_occurrence = registered_occurrence_identity_v1(
        anchor=canonical_anchor,
        context=canonical_context,
        arm=selected_policy.occurrence.arm,
    )
    if (
        selected_policy.occurrence != expected_occurrence
        or operational_terminal.occurrence != expected_occurrence
        or selected_policy.selected_policy_id
        != operational_terminal.selected_policy_id
        or selected_policy.operational_policy_source_artifact_id
        != operational_terminal.operational_result_artifact_id
    ):
        raise V072IndependentExactGroundEvaluationViolation(
            "registered operational terminal/selected policy was "
            "transplanted across the frozen 15-occurrence schedule"
        )
    root_state = registered_observer.HeldoutSymbolicGraphStateV2(
        canonical_context.root_ranks
    )
    root_catalogue = registered_observer.legal_action_catalogue_v2(
        canonical_context,
        root_state,
        registered_prereg.HORIZON,
    )
    if selected_policy.root_decision.state != root_state:
        raise V072IndependentExactGroundEvaluationViolation(
            "registered fixed-kappa root state is not the context root"
        )
    for decision in (
        selected_policy.root_decision,
        *selected_policy.child_decisions,
    ):
        catalogue = registered_observer.legal_action_catalogue_v2(
            canonical_context,
            decision.state,
            decision.remaining_horizon,
        )
        expected_semantic_ids = tuple(
            registered_observer.observation_row_binding_v2(
                canonical_context,
                catalogue,
                action,
            ).row_binding_id
            for action in decision.ground_actions
            if action in catalogue.actions
        )
        if (
            len(expected_semantic_ids) != len(decision.ground_actions)
            or expected_semantic_ids != decision.ground_semantic_action_ids
        ):
            raise V072IndependentExactGroundEvaluationViolation(
                "registered fixed-kappa action support is illegal or its "
                "semantic action identities were altered"
            )
    return (
        canonical_anchor,
        canonical_context,
        operational_terminal,
        selected_policy,
    )


def _evaluate_registered_exact_ground(
    *,
    anchor: final_authority.V072RemoteMainAnchorV1,
    context: registered_prereg.HeldoutPublicGraphContextV2,
    operational_terminal: RegisteredOccurrenceOperationalTerminalV1,
    operational_policy: RegisteredOperationalSelectedPolicyV1,
) -> RegisteredIndependentExactGroundEvaluationResultV1:
    occurrence = operational_policy.occurrence
    row_cache: dict[
        tuple[str, int, tuple[int, int, int]],
        RegisteredExactGroundRowV1,
    ] = {}
    exact_atom_calls = 0

    def row_for(
        state: registered_observer.HeldoutSymbolicGraphStateV2,
        remaining_horizon: int,
        action: tuple[int, int, int],
    ) -> RegisteredExactGroundRowV1:
        nonlocal exact_atom_calls
        key = state.state_id, remaining_horizon, action
        if key not in row_cache:
            catalogue = registered_observer.legal_action_catalogue_v2(
                context,
                state,
                remaining_horizon,
            )
            atoms = tuple(
                sorted(
                    registered_observer.evaluation_only_exact_atoms_v2(
                        anchor,
                        context,
                        catalogue,
                        action,
                    ),
                    key=lambda item: item.atom_id,
                )
            )
            exact_atom_calls += 1
            row_cache[key] = RegisteredExactGroundRowV1(
                anchor.anchor_id,
                atoms[0].environment_manifest_id,
                occurrence.occurrence_id,
                context.context_id,
                catalogue,
                action,
                atoms,
            )
        return row_cache[key]

    root_state = registered_observer.HeldoutSymbolicGraphStateV2(
        context.root_ranks
    )
    root_catalogue = registered_observer.legal_action_catalogue_v2(
        context,
        root_state,
        registered_prereg.HORIZON,
    )
    root_specs: list[GenericH2RootActionV1] = []
    states_by_key: dict[
        tuple[int, ...],
        registered_observer.HeldoutSymbolicGraphStateV2,
    ] = {}
    for root_action in root_catalogue.actions:
        root_row = row_for(
            root_state,
            registered_prereg.HORIZON,
            root_action,
        )
        active_probabilities: dict[
            registered_observer.HeldoutSymbolicGraphStateV2,
            Fraction,
        ] = {}
        root_failure_probability = Fraction(0)
        for atom in root_row.atoms:
            if atom.failure:
                root_failure_probability += atom.probability
            elif not atom.terminal:
                active_probabilities[atom.next_state] = (
                    active_probabilities.get(atom.next_state, Fraction(0))
                    + atom.probability
                )
        child_specs: list[GenericH2ChildBranchV1] = []
        for child_state, child_probability in sorted(
            active_probabilities.items(),
            key=lambda item: item[0].ranks,
        ):
            existing_state = states_by_key.get(child_state.ranks)
            if existing_state is not None and existing_state != child_state:
                raise RuntimeError(
                    "one semantic state key names different ground states"
                )
            states_by_key[child_state.ranks] = child_state
            catalogue = registered_observer.legal_action_catalogue_v2(
                context,
                child_state,
                1,
            )
            child_specs.append(
                GenericH2ChildBranchV1(
                    child_state.ranks,
                    child_probability,
                    tuple(
                        GenericH2ChildActionV1(
                            child_action,
                            row_for(
                                child_state,
                                1,
                                child_action,
                            ).reward,
                            row_for(
                                child_state,
                                1,
                                child_action,
                            ).failure_probability,
                        )
                        for child_action in catalogue.actions
                    ),
                )
            )
        root_specs.append(
            GenericH2RootActionV1(
                root_action,
                root_row.reward,
                root_failure_probability,
                tuple(child_specs),
            )
        )
    generic_core = solve_generic_h2_deterministic_core_v1(
        root_actions=tuple(root_specs),
        risk_tolerance=context.risk_tolerance,
    )
    optimal_generic = generic_core.optimal_policy
    optimal_policy = (
        None
        if optimal_generic is None
        else RegisteredExactGroundPolicyWitnessV1(
            occurrence.occurrence_id,
            context.context_id,
            optimal_generic.root_action,
            tuple(
                sorted(
                    (
                        RegisteredGroundChildDecisionV1(
                            occurrence.occurrence_id,
                            context.context_id,
                            states_by_key[state_key],
                            action,
                        )
                        for state_key, action
                        in optimal_generic.child_actions
                    ),
                    key=lambda item: item.semantic_key,
                )
            ),
            optimal_generic.expected_reward,
            optimal_generic.failure_probability,
        )
    )

    selected_decisions = tuple(
        sorted(
            operational_policy.child_decisions,
            key=lambda item: item.semantic_key,
        )
    )
    child_by_state = {
        item.state.ranks: item for item in selected_decisions
    }
    selected_root_specs: list[
        tuple[Fraction, GenericH2RootActionV1]
    ] = []
    root_by_action = {item.action: item for item in root_specs}
    for action, weight in zip(
        operational_policy.root_decision.ground_actions,
        operational_policy.root_decision.uniform_weights,
        strict=True,
    ):
        root_spec = root_by_action.get(action)
        if root_spec is None:
            raise V072IndependentExactGroundEvaluationViolation(
                "fixed-kappa root realization is absent from exact ground"
            )
        selected_root_specs.append((weight, root_spec))
    required_child_states = {
        branch.state_key
        for _, root_spec in selected_root_specs
        for branch in root_spec.child_branches
    }
    if not required_child_states <= set(child_by_state):
        raise V072IndependentExactGroundEvaluationViolation(
            "fixed-kappa selected policy does not cover the union of child "
            "states reachable under every root realization"
        )
    for decision in selected_decisions:
        if states_by_key.get(decision.state.ranks) != decision.state:
            raise V072IndependentExactGroundEvaluationViolation(
                "selected-policy state was re-signed or is unreachable"
            )
    selected_reward = Fraction(0)
    selected_failure = Fraction(0)
    for root_weight, root_spec in selected_root_specs:
        conditional_reward = root_spec.reward
        conditional_failure = root_spec.immediate_failure_probability
        for branch in root_spec.child_branches:
            decision = child_by_state[branch.state_key]
            option_by_action = {
                item.action: item for item in branch.actions
            }
            child_reward = Fraction(0)
            child_failure = Fraction(0)
            for action, weight in zip(
                decision.ground_actions,
                decision.uniform_weights,
                strict=True,
            ):
                option = option_by_action.get(action)
                if option is None:
                    raise V072IndependentExactGroundEvaluationViolation(
                        "fixed-kappa child realization is absent from exact "
                        "ground"
                    )
                child_reward += weight * option.reward
                child_failure += weight * option.failure_probability
            conditional_reward += branch.probability * child_reward
            conditional_failure += branch.probability * child_failure
        selected_reward += root_weight * conditional_reward
        selected_failure += root_weight * conditional_failure
    selected_witness = RegisteredFixedKappaPolicyWitnessV1(
        occurrence.occurrence_id,
        context.context_id,
        operational_policy.route_kind,
        operational_policy.root_decision,
        selected_decisions,
        selected_reward,
        selected_failure,
    )
    risk_pass = selected_failure <= context.risk_tolerance
    if optimal_policy is None or not risk_pass:
        regret = None
        normalized_regret = None
        regret_pass = False
    else:
        regret = optimal_policy.expected_reward - selected_reward
        normalized_regret = regret / context.reward_ceiling
        regret_pass = (
            normalized_regret <= context.normalized_regret_tolerance
        )
    status = (
        RegisteredExactGroundEvaluationStatusV1.GROUND_QUERY_INFEASIBLE
        if optimal_policy is None
        else (
            RegisteredExactGroundEvaluationStatusV1
            .SELECTED_POLICY_RISK_VIOLATION
            if not risk_pass
            else (
                RegisteredExactGroundEvaluationStatusV1
                .SELECTED_POLICY_REGRET_VIOLATION
                if not regret_pass
                else (
                    RegisteredExactGroundEvaluationStatusV1
                    .CERTIFICATE_METRICS_PASS
                )
            )
        )
    )
    rows = tuple(
        sorted(row_cache.values(), key=lambda item: item.row_id)
    )
    work = RegisteredExactGroundEvaluationWorkV1(
        exact_atom_calls,
        len(rows),
        sum(len(row.atoms) for row in rows),
        generic_core.candidate_extensions,
        generic_core.dominance_comparisons,
        generic_core.frontier_points_retained,
        len(operational_policy.root_decision.ground_actions)
        + sum(len(item.ground_actions) for item in selected_decisions),
    )
    return RegisteredIndependentExactGroundEvaluationResultV1(
        anchor.anchor_id,
        occurrence,
        operational_terminal.terminal_id,
        operational_policy.selected_policy_id,
        status,
        rows,
        optimal_policy,
        selected_witness,
        (
            None
            if optimal_policy is None
            else optimal_policy.expected_reward
        ),
        (
            None
            if optimal_policy is None
            else optimal_policy.failure_probability
        ),
        selected_reward,
        selected_failure,
        regret,
        normalized_regret,
        risk_pass,
        regret_pass,
        risk_pass and regret_pass,
        work,
    )


def evaluate_registered_independent_exact_ground_v1(
    *,
    anchor: Any,
    context: Any,
    operational_terminal: Any,
    selected_policy: Any,
) -> RegisteredIndependentExactGroundEvaluationResultV1:
    """Recompute H=2 ground optimum and one operational policy exactly."""

    (
        canonical_anchor,
        canonical_context,
        canonical_terminal,
        canonical_policy,
    ) = _validate_registered_evaluation_inputs(
        anchor=anchor,
        context=context,
        operational_terminal=operational_terminal,
        selected_policy=selected_policy,
    )
    return _evaluate_registered_exact_ground(
        anchor=canonical_anchor,
        context=canonical_context,
        operational_terminal=canonical_terminal,
        operational_policy=canonical_policy,
    )


__all__ = [
    "DEVELOPMENT_SCOPE",
    "EVALUATION_LANE",
    "ExactGroundChildDecisionV1",
    "ExactGroundEvaluationStatusV1",
    "ExactGroundEvaluationWorkV1",
    "ExactGroundPolicyV1",
    "ExactGroundRowV1",
    "ExactGroundTransitionV1",
    "GenericH2ChildActionV1",
    "GenericH2ChildBranchV1",
    "GenericH2DeterministicCoreResultV1",
    "GenericH2DeterministicPolicyV1",
    "GenericH2FixedKappaPolicyV1",
    "GenericH2RootActionV1",
    "GenericH2UniformKappaDecisionV1",
    "IndependentExactGroundEvaluationResultV1",
    "ExactGroundSameImplementationReplayVerificationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REGISTERED_EVALUATION_ALLOWED",
    "REGISTERED_OPERATIONAL_TERMINAL_AUTHORITY_ENABLED",
    "REGISTERED_OPERATIONAL_TERMINAL_BLOCKER",
    "RegisteredExactGroundSemanticAnchorDraftV1",
    "RegisteredExactGroundEvaluationStatusV1",
    "RegisteredExactGroundEvaluationWorkV1",
    "RegisteredExactGroundPolicyWitnessV1",
    "RegisteredExactGroundRowV1",
    "RegisteredFixedKappaDecisionV1",
    "RegisteredFixedKappaPolicyWitnessV1",
    "RegisteredGroundChildDecisionV1",
    "RegisteredIndependentExactGroundEvaluationLocked",
    "RegisteredIndependentExactGroundEvaluationResultV1",
    "RegisteredOccurrenceIdentityV1",
    "RegisteredOccurrenceOperationalTerminalV1",
    "RegisteredOccurrenceOperationalTerminalRefDraftV1",
    "RegisteredOperationalTerminalPolicyBundleV1",
    "RegisteredOperationalSelectedPolicyV1",
    "SCHEMA_VERSION",
    "V072IndependentExactGroundEvaluationViolation",
    "DevelopmentExactGroundContextV1",
    "DevelopmentExactGroundQueryV1",
    "DevelopmentExactGroundSemanticAnchorV1",
    "DevelopmentExactGroundTerminalRefV1",
    "DevelopmentExactHiddenLawV1",
    "development_exact_ground_k4_context_v1",
    "development_exact_ground_k5_context_v1",
    "development_exact_ground_query_v1",
    "development_exact_ground_terminal_ref_v1",
    "evaluate_development_independent_exact_ground_v1",
    "evaluate_development_h2_generic_dp_control_v1",
    "evaluate_generic_h2_deterministic_policy_v1",
    "evaluate_generic_h2_fixed_kappa_policy_v1",
    "evaluate_registered_independent_exact_ground_v1",
    "mint_registered_occurrence_operational_terminal_policy_v1",
    "registered_occurrence_identity_v1",
    "solve_generic_h2_deterministic_core_v1",
    "verify_development_exact_ground_same_implementation_replay_v1",
]
