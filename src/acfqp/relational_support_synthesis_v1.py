"""Observation-driven relational coordinate and support synthesis.

V0-064 removes the known square-symmetry canonicalizer, the handwritten
survivor labels, and the six named safe-chain rows from the production
construction path.  A source-only producer receives anonymous board/action
observations and a small typed relational grammar.  It closes that grammar,
selects a state/action coordinate pair by complete observed congruence, and
derives content-addressed support templates and a nonauthoritative plan
proposal.

Held-out structural contexts use rank-relative spawn supports that were not
present as source context identities.  Their dynamics start entirely unknown.
A failed model-only proof authorizes the selected root support, observed root
successors create the next proof obligations, and a second authorization
acquires only the selected continuation support.  Statistical target
envelopes, not source probabilities, are the certificate authority.

The claim remains bounded.  The low-level cell/incidence primitives and
operators are registered human vocabulary; this module does not invent raw
perception, arbitrary primitives, or a theorem for unseen graph geometries.
"""

from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass
from enum import Enum
from fractions import Fraction
import functools
import hashlib
import inspect
import math
from itertools import combinations, product
from typing import Any, Mapping

from acfqp.core import Outcome, QuerySpec
from acfqp.domains.g2048 import (
    G2048Action,
    G2048Kernel,
    G2048State,
    G2048Status,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.planning.ground import reachable_decision_pairs, solve_ground_pareto


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.28.0"
PROFILE_KEY = "g2048_observation_driven_relational_support_v0"
SUCCESS_STATUS = (
    "CERTIFIED_REGISTERED_OBSERVATION_DRIVEN_RELATIONAL_SUPPORT_FAMILY"
)

GRID_SIZE = 2
RANK_CAP = 6
HORIZON = 2
RISK_TOLERANCE = Fraction(1, 20)
NORMALIZER = Fraction(2)
SAMPLE_COUNT_PER_GROUND_ROW = 16_384
HOEFFDING_RADIUS = Fraction(1, 60)
PER_COORDINATE_TAIL_UPPER = Fraction(1, 4000)
DRAW_BLOCK_SIZE = 4_096
MAX_PROGRAM_DEPTH = 2
IMPLEMENTATION_SHA256 = (
    "e527c0ff879b36ab07ee8e68f6e7d75ba11145bfcbf8f5b8f57f1e003ad30242"
)
KERNEL_IMPLEMENTATION_SHA256 = (
    "06af469672c48b835b2ae2eb836e1d5cd7a26ad6d44cb00a3a427593a5d6d217"
)

GRAPH_EDGES = ((0, 1), (0, 2), (1, 3), (2, 3))
SOURCE_CONTEXT_PARAMETERS = (
    ("rel_source_r1_p199_200_v0", 1, Fraction(199, 200)),
    ("rel_source_r2_p249_250_v0", 2, Fraction(249, 250)),
    ("rel_source_r3_p999_1000_v0", 3, Fraction(999, 1000)),
)
TARGET_CONTEXT_PARAMETERS = (
    ("rel_target_r2_p199_200_v0", 2, Fraction(199, 200)),
    ("rel_target_r3_p249_250_v0", 3, Fraction(249, 250)),
    ("rel_target_r4_p999_1000_v0", 4, Fraction(999, 1000)),
)

DOMAIN_TAGS = {
    "structural": "acfqp:relational-support-structural:v1",
    "context": "acfqp:relational-support-context:v1",
    "preregistration": "acfqp:relational-support-preregistration:v1",
    "state": "acfqp:relational-raw-state:v1",
    "action": "acfqp:relational-raw-action:v1",
    "outcome": "acfqp:relational-raw-outcome:v1",
    "source_row": "acfqp:relational-source-row:v1",
    "source_log": "acfqp:relational-source-log:v1",
    "expression": "acfqp:relational-coordinate-expression:v1",
    "semantic_signature": "acfqp:relational-program-semantic-signature:v1",
    "program_registry": "acfqp:relational-program-registry:v1",
    "candidate": "acfqp:relational-coordinate-candidate:v1",
    "candidate_trace": "acfqp:relational-candidate-trace:v1",
    "support": "acfqp:relational-anonymous-support-template:v1",
    "proposal": "acfqp:relational-coordinate-support-proposal:v1",
    "authorization": "acfqp:relational-target-row-authorization:v1",
    "sampled_row": "acfqp:relational-packed-sampled-row:v1",
    "evidence": "acfqp:relational-target-evidence:v1",
    "evidence_verification": "acfqp:relational-target-evidence-verification:v1",
    "interval": "acfqp:relational-support-interval:v1",
    "model_row": "acfqp:relational-partial-model-row:v1",
    "model": "acfqp:relational-partial-statistical-model:v1",
    "audit_scope": "acfqp:relational-model-audit-scope:v1",
    "audit": "acfqp:relational-model-only-audit:v1",
    "context_result": "acfqp:relational-target-context-result:v1",
    "occurrence": "acfqp:relational-heldout-occurrence:v1",
    "direct": "acfqp:relational-cold-direct-control:v1",
    "wrong": "acfqp:relational-wrong-proposal-control:v1",
    "calibration": "acfqp:relational-hoeffding-calibration:v1",
    "campaign": "acfqp:relational-support-campaign:v1",
    "verification": "acfqp:relational-support-verification:v1",
}


class RelationalSupportInvariantViolation(ValueError):
    """A source, proposal, target evidence, model, or proof is inconsistent."""


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        domain = DOMAIN_TAGS[role]
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise RelationalSupportInvariantViolation(str(error)) from error
    return hashlib.sha256(domain.encode("utf-8") + b"\x00" + encoded).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise RelationalSupportInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _jsonable(value: Any) -> Any:
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is list:
        return [_jsonable(item) for item in value]
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


def _exact_tuple(value: Any, item_type: type, field: str) -> tuple[Any, ...]:
    if type(value) is not tuple or any(type(item) is not item_type for item in value):
        raise RelationalSupportInvariantViolation(
            f"{field} rejects nested runtime substitutions"
        )
    return value


def _runtime_shape(claimed: Any, expected: Any, path: str) -> None:
    if type(claimed) is not type(expected):
        raise RelationalSupportInvariantViolation(
            f"{path} contains a nested runtime substitution"
        )
    if type(expected) is tuple:
        if len(claimed) != len(expected):
            raise RelationalSupportInvariantViolation(f"{path} length changed")
        for index, (left, right) in enumerate(zip(claimed, expected)):
            _runtime_shape(left, right, f"{path}[{index}]")
        return
    if is_dataclass(expected):
        for field in fields(type(expected)):
            _runtime_shape(
                object.__getattribute__(claimed, field.name),
                object.__getattribute__(expected, field.name),
                f"{path}.{field.name}",
            )


class ContextSplit(str, Enum):
    SOURCE = "SOURCE"
    TARGET = "TARGET"


@dataclass(frozen=True, slots=True)
class RelationalStructuralContextV1:
    context_key: str
    split: ContextSplit
    low_rank: int
    low_rank_probability: Fraction
    graph_edges: tuple[tuple[int, int], ...] = GRAPH_EDGES
    rank_cap: int = RANK_CAP
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE

    def __post_init__(self) -> None:
        expected_parameters = (
            SOURCE_CONTEXT_PARAMETERS
            if self.split is ContextSplit.SOURCE
            else TARGET_CONTEXT_PARAMETERS
        )
        if (
            type(self.context_key) is not str
            or (self.context_key, self.low_rank, self.low_rank_probability)
            not in expected_parameters
            or type(self.low_rank) is not int
            or not 1 <= self.low_rank < self.rank_cap
            or type(self.low_rank_probability) is not Fraction
            or not 0 < self.low_rank_probability < 1
            or self.graph_edges != GRAPH_EDGES
            or self.rank_cap != RANK_CAP
            or self.horizon != HORIZON
            or self.risk_tolerance != RISK_TOLERANCE
        ):
            raise RelationalSupportInvariantViolation(
                "relational structural context is outside the registered family"
            )

    @property
    def high_rank(self) -> int:
        return self.low_rank + 1

    def _structural_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_support_structural.v1",
            "schema_version": SCHEMA_VERSION,
            "grid_size": GRID_SIZE,
            "graph_edges": [list(edge) for edge in self.graph_edges],
            "rank_cap": self.rank_cap,
            "low_rank": self.low_rank,
            "high_rank": self.high_rank,
            "spawn_support": [self.low_rank, self.high_rank],
            "spawn_probabilities": [
                _fdoc(self.low_rank_probability),
                _fdoc(1 - self.low_rank_probability),
            ],
            "kernel_implementation_sha256": KERNEL_IMPLEMENTATION_SHA256,
            "merge_semantics": "selected_equal_pair_single_survivor",
            "spawn_position": "uniform_over_postmerge_empty_cells",
            "post_spawn_failure_check": True,
        }

    @property
    def structural_id(self) -> str:
        return _content_id("structural", self._structural_payload())

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_structural_context.v1",
            "schema_version": SCHEMA_VERSION,
            "context_key": self.context_key,
            "split": self.split.value,
            "structural_id": self.structural_id,
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_relational_contexts_v1(
    split: ContextSplit | None = None,
) -> tuple[RelationalStructuralContextV1, ...]:
    rows = tuple(
        RelationalStructuralContextV1(key, ContextSplit.SOURCE, rank, probability)
        for key, rank, probability in SOURCE_CONTEXT_PARAMETERS
    ) + tuple(
        RelationalStructuralContextV1(key, ContextSplit.TARGET, rank, probability)
        for key, rank, probability in TARGET_CONTEXT_PARAMETERS
    )
    return rows if split is None else tuple(item for item in rows if item.split is split)


@dataclass(frozen=True, slots=True)
class RankRelativeAcquisitionKernelV1(G2048Kernel):
    """Exact kernel restricted to acquisition and standalone evaluation."""

    context_key: str = SOURCE_CONTEXT_PARAMETERS[0][0]
    low_rank: int = 1
    low_rank_probability: Fraction = Fraction(199, 200)

    def __post_init__(self) -> None:
        G2048Kernel.__post_init__(self)
        if (
            self.size != GRID_SIZE
            or type(self.context_key) is not str
            or type(self.low_rank) is not int
            or not 1 <= self.low_rank < self.rank_cap
            or type(self.low_rank_probability) is not Fraction
            or not 0 < self.low_rank_probability < 1
        ):
            raise RelationalSupportInvariantViolation(
                "rank-relative acquisition kernel is invalid"
            )

    @property
    def spawn_distribution(self) -> tuple[tuple[int, Fraction], ...]:
        return (
            (self.low_rank, self.low_rank_probability),
            (self.low_rank + 1, 1 - self.low_rank_probability),
        )

    def sample_transition(
        self,
        state: G2048State,
        action: G2048Action,
        uniform: Fraction,
    ) -> tuple[G2048State, Fraction, bool, bool]:
        """Return one transition sample without exposing a probability table."""

        self._validate_state(state)
        if action not in self.actions(state):
            raise RelationalSupportInvariantViolation(
                "generative acquisition action is not legal"
            )
        if type(uniform) is not Fraction or not 0 <= uniform < 1:
            raise RelationalSupportInvariantViolation(
                "generative acquisition uniform is outside [0,1)"
            )
        rank = state.board[action.first]
        board_after_merge = list(state.board)
        board_after_merge[action.first] = 0
        board_after_merge[action.second] = 0
        board_after_merge[action.survivor] = min(rank + 1, self.rank_cap)
        empty_cells = tuple(
            index
            for index, value in enumerate(board_after_merge)
            if value == 0
        )
        scaled = uniform * len(empty_cells)
        cell_ordinal = scaled.numerator // scaled.denominator
        rank_uniform = scaled - cell_ordinal
        spawn_rank = (
            self.low_rank
            if rank_uniform < self.low_rank_probability
            else self.low_rank + 1
        )
        next_board = board_after_merge.copy()
        next_board[empty_cells[cell_ordinal]] = spawn_rank
        provisional = G2048State(tuple(next_board))
        failed = not self.actions(provisional)
        next_state = G2048State(
            provisional.board,
            G2048Status.FAILURE if failed else G2048Status.ACTIVE,
        )
        reward = Fraction(2 ** (rank + 1), 2 ** (self.rank_cap + 1))
        return next_state, reward, failed, failed

    def sample_structural_atom_index(
        self,
        empty_cell_count: int,
        uniform_uint256: int,
    ) -> int:
        """Sample one registered cell/rank atom using exact integer arithmetic."""

        if (
            type(empty_cell_count) is not int
            or empty_cell_count <= 0
            or type(uniform_uint256) is not int
            or not 0 <= uniform_uint256 < 1 << 256
        ):
            raise RelationalSupportInvariantViolation(
                "generative atom sampler input is invalid"
            )
        scaled = uniform_uint256 * empty_cell_count
        cell_ordinal, rank_remainder = divmod(scaled, 1 << 256)
        low_rank = (
            rank_remainder * self.low_rank_probability.denominator
            < self.low_rank_probability.numerator * (1 << 256)
        )
        return 2 * cell_ordinal + (0 if low_rank else 1)


def _kernel_for_context(
    context: RelationalStructuralContextV1,
) -> RankRelativeAcquisitionKernelV1:
    return RankRelativeAcquisitionKernelV1(
        size=GRID_SIZE,
        context_key=context.context_key,
        low_rank=context.low_rank,
        low_rank_probability=context.low_rank_probability,
    )


def _motif_states(
    context: RelationalStructuralContextV1,
) -> tuple[G2048State, ...]:
    """Enumerate raw embeddings from incidence, without a group/orbit prior."""

    states: list[G2048State] = []
    for first, second in context.graph_edges:
        for anchor in range(GRID_SIZE * GRID_SIZE):
            if anchor in (first, second):
                continue
            board = [0] * (GRID_SIZE * GRID_SIZE)
            board[first] = context.low_rank
            board[second] = context.low_rank
            board[anchor] = context.high_rank
            states.append(G2048State(tuple(board)))
    unique = tuple(dict.fromkeys(states))
    if len(unique) != 8:
        raise RelationalSupportInvariantViolation(
            "registered incidence enumeration must yield eight raw embeddings"
        )
    return unique


@dataclass(frozen=True, slots=True)
class RawRelationalStateV1:
    context_id: str
    board: tuple[int, ...]
    status: str
    remaining_horizon: int

    def __post_init__(self) -> None:
        _cid(self.context_id, "raw state context")
        if (
            type(self.board) is not tuple
            or len(self.board) != GRID_SIZE * GRID_SIZE
            or any(type(rank) is not int or not 0 <= rank <= RANK_CAP for rank in self.board)
            or self.status not in (G2048Status.ACTIVE.value, G2048Status.FAILURE.value)
            or type(self.remaining_horizon) is not int
            or not 0 <= self.remaining_horizon <= HORIZON
        ):
            raise RelationalSupportInvariantViolation("raw relational state is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_relational_state.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "board": list(self.board),
            "status": self.status,
            "remaining_horizon": self.remaining_horizon,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


@dataclass(frozen=True, slots=True)
class RawRelationalActionV1:
    state_id: str
    first: int
    second: int
    survivor: int

    def __post_init__(self) -> None:
        _cid(self.state_id, "raw action state")
        if (
            type(self.first) is not int
            or type(self.second) is not int
            or type(self.survivor) is not int
            or not 0 <= self.first < self.second < GRID_SIZE * GRID_SIZE
            or self.survivor not in (self.first, self.second)
        ):
            raise RelationalSupportInvariantViolation("raw action is invalid")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_relational_action.v1",
            "schema_version": SCHEMA_VERSION,
            "state_id": self.state_id,
            "pair": [self.first, self.second],
            "survivor": self.survivor,
        }

    @property
    def action_id(self) -> str:
        return _content_id("action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "action_id": self.action_id}


@dataclass(frozen=True, slots=True)
class RawRelationalOutcomeV1:
    next_state: RawRelationalStateV1
    probability: Fraction
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        if (
            type(self.next_state) is not RawRelationalStateV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.normalized_reward) is not Fraction
            or self.normalized_reward < 0
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure != (self.next_state.status == G2048Status.FAILURE.value)
            or self.terminal != self.failure
        ):
            raise RelationalSupportInvariantViolation(
                "raw relational outcome is invalid"
            )

    def _payload(self, *, include_probability: bool = True) -> dict[str, Any]:
        return {
            "schema": "acfqp.raw_relational_outcome.v1",
            "schema_version": SCHEMA_VERSION,
            "next_state": self.next_state.to_document(),
            "probability": _fdoc(self.probability) if include_probability else None,
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
        }

    @property
    def outcome_id(self) -> str:
        return _content_id("outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "outcome_id": self.outcome_id}


@dataclass(frozen=True, slots=True)
class SourceObservedGroundRowV1:
    state: RawRelationalStateV1
    action: RawRelationalActionV1
    legal_actions: tuple[RawRelationalActionV1, ...]
    outcomes: tuple[RawRelationalOutcomeV1, ...]

    def __post_init__(self) -> None:
        _exact_tuple(self.legal_actions, RawRelationalActionV1, "source legal actions")
        _exact_tuple(self.outcomes, RawRelationalOutcomeV1, "source outcomes")
        if (
            type(self.state) is not RawRelationalStateV1
            or type(self.action) is not RawRelationalActionV1
            or self.action.state_id != self.state.state_id
            or self.action not in self.legal_actions
            or any(item.state_id != self.state.state_id for item in self.legal_actions)
            or any(item.next_state.context_id != self.state.context_id for item in self.outcomes)
            or sum((item.probability for item in self.outcomes), Fraction(0)) != 1
        ):
            raise RelationalSupportInvariantViolation(
                "source observed ground row is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.source_observed_relational_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "state": self.state.to_document(),
            "action": self.action.to_document(),
            "legal_actions": [item.to_document() for item in self.legal_actions],
            "outcomes": [item.to_document() for item in self.outcomes],
        }

    @property
    def row_id(self) -> str:
        return _content_id("source_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "row_id": self.row_id}


@dataclass(frozen=True, slots=True)
class SourceRelationalObservationLogV1:
    contexts: tuple[RelationalStructuralContextV1, ...]
    rows: tuple[SourceObservedGroundRowV1, ...]
    query_inputs_used: int = 0
    target_inputs_used: int = 0
    group_prior_used: bool = False
    named_semantic_rows_used: bool = False
    complete_two_step_source_support: bool = True

    def __post_init__(self) -> None:
        _exact_tuple(self.contexts, RelationalStructuralContextV1, "source contexts")
        _exact_tuple(self.rows, SourceObservedGroundRowV1, "source rows")
        expected = registered_relational_contexts_v1(ContextSplit.SOURCE)
        if (
            self.contexts != expected
            or len(self.rows) != 144
            or any(
                row.state.context_id not in {item.context_id for item in self.contexts}
                for row in self.rows
            )
            or tuple(row.row_id for row in self.rows)
            != tuple(sorted({row.row_id for row in self.rows}))
            or self.query_inputs_used != 0
            or self.target_inputs_used != 0
            or self.group_prior_used is not False
            or self.named_semantic_rows_used is not False
            or self.complete_two_step_source_support is not True
        ):
            raise RelationalSupportInvariantViolation(
                "source observation log scope or chronology changed"
            )
        _validate_source_log_coverage_v1(self)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.source_relational_observation_log.v1",
            "schema_version": SCHEMA_VERSION,
            "contexts": [item.to_document() for item in self.contexts],
            "rows": [item.to_document() for item in self.rows],
            "query_inputs_used": self.query_inputs_used,
            "target_inputs_used": self.target_inputs_used,
            "group_prior_used": self.group_prior_used,
            "named_semantic_rows_used": self.named_semantic_rows_used,
            "complete_two_step_source_support": self.complete_two_step_source_support,
        }

    @property
    def log_id(self) -> str:
        return _content_id("source_log", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "log_id": self.log_id}


def _validate_source_log_coverage_v1(
    source_log: SourceRelationalObservationLogV1,
) -> None:
    """Prove complete two-step action closure from the supplied rows themselves."""

    for context in source_log.contexts:
        context_rows = tuple(
            row
            for row in source_log.rows
            if row.state.context_id == context.context_id
        )
        if len(context_rows) != 48:
            raise RelationalSupportInvariantViolation(
                "each source context requires exactly 48 rows"
            )
        rows_by_state: dict[str, list[SourceObservedGroundRowV1]] = {}
        state_by_id: dict[str, RawRelationalStateV1] = {}
        for row in context_rows:
            rows_by_state.setdefault(row.state.state_id, []).append(row)
            state_by_id[row.state.state_id] = row.state
        for state_id, state_rows in rows_by_state.items():
            legal = state_rows[0].legal_actions
            if (
                any(row.legal_actions != legal for row in state_rows)
                or {row.action.action_id for row in state_rows}
                != {action.action_id for action in legal}
                or len(state_rows) != len(legal)
                or any(action.state_id != state_id for action in legal)
            ):
                raise RelationalSupportInvariantViolation(
                    "source log does not close every observed state under legal actions"
                )
        root_states = {
            row.state.board
            for row in context_rows
            if row.state.remaining_horizon == HORIZON
        }
        if root_states != {state.board for state in _motif_states(context)}:
            raise RelationalSupportInvariantViolation(
                "source log root coverage differs from incidence enumeration"
            )
        expected_successor_ids = {
            outcome.next_state.state_id
            for row in context_rows
            if row.state.remaining_horizon == HORIZON
            for outcome in row.outcomes
            if not outcome.failure
            and not outcome.terminal
            and outcome.next_state.remaining_horizon == HORIZON - 1
        }
        observed_successor_ids = {
            state_id
            for state_id, state in state_by_id.items()
            if state.remaining_horizon == HORIZON - 1
        }
        if expected_successor_ids != observed_successor_ids:
            raise RelationalSupportInvariantViolation(
                "source log continuation coverage is incomplete or extraneous"
            )


def _raw_state(
    context: RelationalStructuralContextV1,
    state: G2048State,
    remaining: int,
) -> RawRelationalStateV1:
    return RawRelationalStateV1(
        context.context_id,
        state.board,
        state.status.value,
        remaining,
    )


def _raw_action(
    state: RawRelationalStateV1,
    action: G2048Action,
) -> RawRelationalActionV1:
    return RawRelationalActionV1(
        state.state_id,
        action.first,
        action.second,
        action.survivor,
    )


def _source_row(
    context: RelationalStructuralContextV1,
    kernel: RankRelativeAcquisitionKernelV1,
    state: G2048State,
    action: G2048Action,
    remaining: int,
) -> SourceObservedGroundRowV1:
    raw_state = _raw_state(context, state, remaining)
    legal = tuple(_raw_action(raw_state, item) for item in kernel.actions(state))
    outcomes = tuple(
        RawRelationalOutcomeV1(
            _raw_state(context, outcome.next_state, remaining - 1),
            outcome.probability,
            dict(outcome.reward_features)["merge"] / NORMALIZER,
            outcome.failure,
            outcome.terminal,
        )
        for outcome in kernel.step(state, action)
    )
    return SourceObservedGroundRowV1(
        raw_state,
        _raw_action(raw_state, action),
        legal,
        outcomes,
    )


def acquire_source_relational_observations_v1(
    contexts: tuple[RelationalStructuralContextV1, ...],
) -> SourceRelationalObservationLogV1:
    """Acquire complete H2 source rows; the proposer itself receives no kernel."""

    if contexts != registered_relational_contexts_v1(ContextSplit.SOURCE):
        raise RelationalSupportInvariantViolation(
            "source acquisition requires the frozen source contexts"
        )
    rows: dict[str, SourceObservedGroundRowV1] = {}
    for context in contexts:
        kernel = _kernel_for_context(context)
        successors: set[G2048State] = set()
        for state in _motif_states(context):
            for action in kernel.actions(state):
                row = _source_row(context, kernel, state, action, HORIZON)
                rows[row.row_id] = row
                for outcome in kernel.step(state, action):
                    if not outcome.failure and not outcome.terminal:
                        successors.add(outcome.next_state)
        for state in sorted(successors, key=lambda item: (item.board, item.status.value)):
            for action in kernel.actions(state):
                row = _source_row(context, kernel, state, action, 1)
                rows[row.row_id] = row
    return SourceRelationalObservationLogV1(
        contexts,
        tuple(sorted(rows.values(), key=lambda item: item.row_id)),
    )


class ProgramType(str, Enum):
    CELL_SET = "CELL_SET"
    ACTION_SET = "ACTION_SET"
    CELL = "CELL"
    INTEGER = "INTEGER"
    BOOLEAN = "BOOLEAN"


class ProgramContext(str, Enum):
    STATE = "STATE"
    STATE_ACTION = "STATE_ACTION"


_PRIMITIVES: dict[str, tuple[ProgramType, ProgramContext, bool]] = {
    "occupied_cells": (ProgramType.CELL_SET, ProgramContext.STATE, False),
    "legal_actions": (ProgramType.ACTION_SET, ProgramContext.STATE, False),
    "action_pair_cells": (ProgramType.CELL_SET, ProgramContext.STATE_ACTION, False),
    "survivor_cell": (ProgramType.CELL, ProgramContext.STATE_ACTION, False),
    "integer_literal": (ProgramType.INTEGER, ProgramContext.STATE, True),
}
_OPERATORS: dict[str, tuple[tuple[ProgramType, ...], ProgramType]] = {
    "cardinality_cells": ((ProgramType.CELL_SET,), ProgramType.INTEGER),
    "cardinality_actions": ((ProgramType.ACTION_SET,), ProgramType.INTEGER),
    "adjacent_filter": (
        (ProgramType.CELL, ProgramType.CELL_SET),
        ProgramType.CELL_SET,
    ),
    "set_difference": (
        (ProgramType.CELL_SET, ProgramType.CELL_SET),
        ProgramType.CELL_SET,
    ),
    "subtract": ((ProgramType.INTEGER, ProgramType.INTEGER), ProgramType.INTEGER),
    "equals": ((ProgramType.INTEGER, ProgramType.INTEGER), ProgramType.BOOLEAN),
}
_OPERATION_ORDER = tuple(_PRIMITIVES) + tuple(_OPERATORS)


@dataclass(frozen=True, slots=True)
class RelationalCoordinateProgramV1:
    operation: str
    result_type: ProgramType
    context: ProgramContext
    arguments: tuple["RelationalCoordinateProgramV1", ...] = ()
    literal: int | None = None

    def __post_init__(self) -> None:
        if type(self.operation) is not str:
            raise RelationalSupportInvariantViolation("program operation is invalid")
        _exact_tuple(
            self.arguments,
            RelationalCoordinateProgramV1,
            "program arguments",
        )
        primitive = _PRIMITIVES.get(self.operation)
        if primitive is not None:
            result_type, context, literal_required = primitive
            if (
                self.arguments
                or self.result_type is not result_type
                or self.context is not context
                or literal_required != (self.literal is not None)
                or (
                    self.literal is not None
                    and (type(self.literal) is not int or self.literal not in (0, 1, 2))
                )
            ):
                raise RelationalSupportInvariantViolation(
                    "program primitive contract mismatch"
                )
            return
        operator = _OPERATORS.get(self.operation)
        if operator is None or self.literal is not None:
            raise RelationalSupportInvariantViolation(
                "program operator is unregistered"
            )
        argument_types, result_type = operator
        context = (
            ProgramContext.STATE_ACTION
            if any(item.context is ProgramContext.STATE_ACTION for item in self.arguments)
            else ProgramContext.STATE
        )
        if (
            tuple(item.result_type for item in self.arguments) != argument_types
            or self.result_type is not result_type
            or self.context is not context
        ):
            raise RelationalSupportInvariantViolation(
                "program operator contract mismatch"
            )

    @property
    def depth(self) -> int:
        return 0 if not self.arguments else 1 + max(item.depth for item in self.arguments)

    @property
    def node_count(self) -> int:
        return 1 + sum(item.node_count for item in self.arguments)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_coordinate_program.v1",
            "schema_version": SCHEMA_VERSION,
            "operation": self.operation,
            "result_type": self.result_type.value,
            "context": self.context.value,
            "arguments": [item.to_document() for item in self.arguments],
            "literal": self.literal,
        }

    @property
    def program_id(self) -> str:
        return _content_id("expression", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "program_id": self.program_id}


def _primitive(
    operation: str,
    literal: int | None = None,
) -> RelationalCoordinateProgramV1:
    result_type, context, _ = _PRIMITIVES[operation]
    return RelationalCoordinateProgramV1(
        operation,
        result_type,
        context,
        (),
        literal,
    )


def _operator(
    operation: str,
    arguments: tuple[RelationalCoordinateProgramV1, ...],
) -> RelationalCoordinateProgramV1:
    context = (
        ProgramContext.STATE_ACTION
        if any(item.context is ProgramContext.STATE_ACTION for item in arguments)
        else ProgramContext.STATE
    )
    return RelationalCoordinateProgramV1(
        operation,
        _OPERATORS[operation][1],
        context,
        arguments,
    )


def _program_complexity(program: RelationalCoordinateProgramV1) -> tuple[Any, ...]:
    return (
        program.node_count,
        program.depth,
        _OPERATION_ORDER.index(program.operation),
        tuple(_program_complexity(item) for item in program.arguments),
        -1 if program.literal is None else program.literal,
        program.program_id,
    )


@dataclass(frozen=True, slots=True)
class _EvaluationCovariate:
    state: RawRelationalStateV1
    action: RawRelationalActionV1 | None
    legal_actions: tuple[RawRelationalActionV1, ...]


def _eval_program(
    program: RelationalCoordinateProgramV1,
    covariate: _EvaluationCovariate,
) -> Any:
    operation = program.operation
    if operation == "occupied_cells":
        return tuple(index for index, rank in enumerate(covariate.state.board) if rank)
    if operation == "legal_actions":
        return tuple(item.action_id for item in covariate.legal_actions)
    if operation == "action_pair_cells":
        if covariate.action is None:
            raise RelationalSupportInvariantViolation(
                "state-action program lacks an action"
            )
        return (covariate.action.first, covariate.action.second)
    if operation == "survivor_cell":
        if covariate.action is None:
            raise RelationalSupportInvariantViolation(
                "state-action program lacks an action"
            )
        return covariate.action.survivor
    if operation == "integer_literal":
        return program.literal
    values = tuple(_eval_program(item, covariate) for item in program.arguments)
    if operation in ("cardinality_cells", "cardinality_actions"):
        return len(values[0])
    if operation == "adjacent_filter":
        cell, cells = values
        return tuple(
            item
            for item in cells
            if tuple(sorted((cell, item))) in GRAPH_EDGES
        )
    if operation == "set_difference":
        excluded = set(values[1])
        return tuple(item for item in values[0] if item not in excluded)
    if operation == "subtract":
        return values[0] - values[1]
    if operation == "equals":
        return values[0] == values[1]
    raise AssertionError("unreachable registered relational operation")


def _normalized_program_value(
    program: RelationalCoordinateProgramV1,
    value: Any,
) -> tuple[str, Any]:
    if program.result_type in (ProgramType.CELL_SET, ProgramType.ACTION_SET):
        if type(value) is not tuple:
            raise RelationalSupportInvariantViolation("program set value is invalid")
        return (program.result_type.value, tuple(value))
    if program.result_type in (ProgramType.CELL, ProgramType.INTEGER):
        if type(value) is not int:
            raise RelationalSupportInvariantViolation("program integer value is invalid")
        return (program.result_type.value, value)
    if program.result_type is ProgramType.BOOLEAN:
        if type(value) is not bool:
            raise RelationalSupportInvariantViolation("program boolean value is invalid")
        return (program.result_type.value, value)
    raise AssertionError("unreachable program type")


def _source_covariates(
    source_log: SourceRelationalObservationLogV1,
) -> tuple[_EvaluationCovariate, ...]:
    state_covariates: dict[str, _EvaluationCovariate] = {}
    action_covariates: list[_EvaluationCovariate] = []
    for row in source_log.rows:
        state_covariates[row.state.state_id] = _EvaluationCovariate(
            row.state,
            None,
            row.legal_actions,
        )
        action_covariates.append(
            _EvaluationCovariate(row.state, row.action, row.legal_actions)
        )
    return tuple(
        sorted(state_covariates.values(), key=lambda item: item.state.state_id)
    ) + tuple(
        sorted(
            action_covariates,
            key=lambda item: (
                item.state.state_id,
                "" if item.action is None else item.action.action_id,
            ),
        )
    )


@dataclass(frozen=True, slots=True)
class ProgramClosureSummaryV1:
    depth: int
    raw_program_count: int
    new_semantic_count: int
    cumulative_semantic_count: int

    def to_document(self) -> dict[str, Any]:
        return {
            "depth": self.depth,
            "raw_program_count": self.raw_program_count,
            "new_semantic_count": self.new_semantic_count,
            "cumulative_semantic_count": self.cumulative_semantic_count,
        }


@dataclass(frozen=True, slots=True)
class RelationalProgramRegistryV1:
    source_log_id: str
    summaries: tuple[ProgramClosureSummaryV1, ...]
    programs: tuple[RelationalCoordinateProgramV1, ...]
    max_depth: int = MAX_PROGRAM_DEPTH
    semantic_dedup_rule: str = (
        "typed_context_full_source_covariate_signature_keep_minimum_ast_v1"
    )

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "program registry source log")
        _exact_tuple(self.summaries, ProgramClosureSummaryV1, "closure summaries")
        _exact_tuple(self.programs, RelationalCoordinateProgramV1, "closure programs")
        if (
            not self.programs
            or tuple(item.program_id for item in self.programs)
            != tuple(sorted({item.program_id for item in self.programs}))
            or self.max_depth != MAX_PROGRAM_DEPTH
        ):
            raise RelationalSupportInvariantViolation(
                "program registry ordering or cap changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_program_registry.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "summaries": [item.to_document() for item in self.summaries],
            "programs": [item.to_document() for item in self.programs],
            "max_depth": self.max_depth,
            "semantic_dedup_rule": self.semantic_dedup_rule,
            "human_selected_program_id": None,
        }

    @property
    def registry_id(self) -> str:
        return _content_id("program_registry", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "registry_id": self.registry_id}


def generate_relational_program_closure_v1(
    source_log: SourceRelationalObservationLogV1,
) -> RelationalProgramRegistryV1:
    """Bottom-up typed closure with source-observation semantic deduplication."""

    if type(source_log) is not SourceRelationalObservationLogV1:
        raise RelationalSupportInvariantViolation(
            "program closure rejects substituted source logs"
        )
    covariates = _source_covariates(source_log)
    retained: dict[
        tuple[Any, ...],
        RelationalCoordinateProgramV1,
    ] = {}
    summaries: list[ProgramClosureSummaryV1] = []

    bases = (
        _primitive("occupied_cells"),
        _primitive("legal_actions"),
        _primitive("action_pair_cells"),
        _primitive("survivor_cell"),
        *(_primitive("integer_literal", literal) for literal in (0, 1, 2)),
    )

    def signature(program: RelationalCoordinateProgramV1) -> tuple[Any, ...]:
        relevant = tuple(
            item
            for item in covariates
            if (
                program.context is ProgramContext.STATE_ACTION
                or item.action is None
            )
            and not (
                program.context is ProgramContext.STATE_ACTION
                and item.action is None
            )
        )
        values = tuple(
            _normalized_program_value(program, _eval_program(program, item))
            for item in relevant
        )
        return (program.result_type.value, program.context.value, values)

    for program in bases:
        key = signature(program)
        prior = retained.get(key)
        if prior is None or _program_complexity(program) < _program_complexity(prior):
            retained[key] = program
    summaries.append(ProgramClosureSummaryV1(0, len(bases), len(retained), len(retained)))

    for depth in range(1, MAX_PROGRAM_DEPTH + 1):
        available = tuple(retained.values())
        by_type = {
            program_type: tuple(
                item for item in available if item.result_type is program_type
            )
            for program_type in ProgramType
        }
        generated: dict[str, RelationalCoordinateProgramV1] = {}
        for operation, (argument_types, _) in _OPERATORS.items():
            for arguments in product(*(by_type[item] for item in argument_types)):
                program = _operator(operation, arguments)
                if program.depth == depth:
                    generated[program.program_id] = program
        raw = tuple(sorted(generated.values(), key=_program_complexity))
        before = len(retained)
        for program in raw:
            key = signature(program)
            prior = retained.get(key)
            if prior is None or _program_complexity(program) < _program_complexity(prior):
                retained[key] = program
        summaries.append(
            ProgramClosureSummaryV1(
                depth,
                len(raw),
                len(retained) - before,
                len(retained),
            )
        )
    programs = tuple(sorted(retained.values(), key=lambda item: item.program_id))
    return RelationalProgramRegistryV1(
        source_log.log_id,
        tuple(summaries),
        programs,
    )


def _scalar_programs(
    registry: RelationalProgramRegistryV1,
    context: ProgramContext,
) -> tuple[RelationalCoordinateProgramV1, ...]:
    return tuple(
        item
        for item in registry.programs
        if item.context is context
        and item.result_type in (ProgramType.INTEGER, ProgramType.BOOLEAN)
    )


def _state_catalogues(
    source_log: SourceRelationalObservationLogV1,
) -> dict[str, tuple[RawRelationalActionV1, ...]]:
    result: dict[str, tuple[RawRelationalActionV1, ...]] = {}
    for row in source_log.rows:
        prior = result.get(row.state.state_id)
        if prior is not None and prior != row.legal_actions:
            raise RelationalSupportInvariantViolation(
                "source state has inconsistent legal-action catalogues"
            )
        result[row.state.state_id] = row.legal_actions
    return result


def _state_value(
    program: RelationalCoordinateProgramV1 | None,
    state: RawRelationalStateV1,
    legal_actions: tuple[RawRelationalActionV1, ...],
) -> tuple[str, Any]:
    if program is None:
        return ("NULL", None)
    return _normalized_program_value(
        program,
        _eval_program(program, _EvaluationCovariate(state, None, legal_actions)),
    )


def _action_value(
    program: RelationalCoordinateProgramV1 | None,
    row: SourceObservedGroundRowV1,
) -> tuple[str, Any]:
    if program is None:
        return ("NULL", None)
    return _normalized_program_value(
        program,
        _eval_program(
            program,
            _EvaluationCovariate(row.state, row.action, row.legal_actions),
        ),
    )


def _aggregate_source_destinations(
    row: SourceObservedGroundRowV1,
    state_program: RelationalCoordinateProgramV1 | None,
    catalogue_by_state: Mapping[str, tuple[RawRelationalActionV1, ...]],
) -> tuple[tuple[tuple[Any, ...], Fraction], ...]:
    masses: dict[tuple[Any, ...], Fraction] = {}
    for outcome in row.outcomes:
        if outcome.failure:
            destination: tuple[Any, ...] = ("FAILURE",)
        elif outcome.next_state.remaining_horizon == 0:
            destination = ("SAFE_TERMINAL",)
        else:
            catalogue = catalogue_by_state.get(outcome.next_state.state_id)
            if catalogue is None:
                raise RelationalSupportInvariantViolation(
                    "source successor lacks a complete action catalogue"
                )
            destination = (
                "ACTIVE",
                outcome.next_state.remaining_horizon,
                _state_value(state_program, outcome.next_state, catalogue),
            )
        masses[destination] = masses.get(destination, Fraction(0)) + outcome.probability
    return tuple(sorted(masses.items(), key=lambda item: repr(item[0])))


def _ordinal_behavior_signature(
    distribution: tuple[tuple[tuple[Any, ...], Fraction], ...],
) -> tuple[tuple[tuple[Any, ...], int], ...]:
    """Discard source magnitudes but retain their observed destination ordering."""

    distinct = tuple(sorted({probability for _, probability in distribution}))
    rank = {probability: index for index, probability in enumerate(distinct)}
    return tuple((destination, rank[probability]) for destination, probability in distribution)


@dataclass(frozen=True, slots=True)
class RelationalCoordinateCandidateV1:
    candidate_index: int
    state_program_id: str | None
    action_program_id: str | None
    source_row_count: int
    abstract_row_count: int
    state_cell_count: int
    alias_pair_count: int
    contradiction_count: int
    availability_violation_count: int
    strict_state_compression: bool
    strict_action_compression: bool
    admissible: bool

    def __post_init__(self) -> None:
        if self.state_program_id is not None:
            _cid(self.state_program_id, "candidate state program")
        if self.action_program_id is not None:
            _cid(self.action_program_id, "candidate action program")
        if (
            type(self.candidate_index) is not int
            or self.candidate_index < 0
            or any(
                type(value) is not int or value < 0
                for value in (
                    self.source_row_count,
                    self.abstract_row_count,
                    self.state_cell_count,
                    self.alias_pair_count,
                    self.contradiction_count,
                    self.availability_violation_count,
                )
            )
            or type(self.strict_state_compression) is not bool
            or type(self.strict_action_compression) is not bool
            or type(self.admissible) is not bool
            or self.admissible
            != (
                self.state_program_id is not None
                and self.action_program_id is not None
                and self.contradiction_count == 0
                and self.availability_violation_count == 0
                and self.strict_state_compression
                and self.strict_action_compression
            )
        ):
            raise RelationalSupportInvariantViolation(
                "coordinate candidate summary is inconsistent"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_coordinate_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "candidate_index": self.candidate_index,
            "state_program_id": self.state_program_id,
            "action_program_id": self.action_program_id,
            "source_row_count": self.source_row_count,
            "abstract_row_count": self.abstract_row_count,
            "state_cell_count": self.state_cell_count,
            "alias_pair_count": self.alias_pair_count,
            "contradiction_count": self.contradiction_count,
            "availability_violation_count": self.availability_violation_count,
            "strict_state_compression": self.strict_state_compression,
            "strict_action_compression": self.strict_action_compression,
            "admissible": self.admissible,
        }

    @property
    def candidate_id(self) -> str:
        return _content_id("candidate", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class RelationalCandidateTraceV1:
    source_log_id: str
    program_registry_id: str
    candidates: tuple[RelationalCoordinateCandidateV1, ...]
    selected_candidate_id: str
    required_candidate_count: int
    evaluated_candidate_count: int
    selection_rule: str = (
        "admissible_then_min_abstract_rows_cells_program_complexity_ids_v1"
    )

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "candidate trace source")
        _cid(self.program_registry_id, "candidate trace registry")
        _cid(self.selected_candidate_id, "candidate trace selection")
        _exact_tuple(self.candidates, RelationalCoordinateCandidateV1, "candidate trace")
        if (
            not self.candidates
            or tuple(item.candidate_index for item in self.candidates)
            != tuple(range(len(self.candidates)))
            or self.required_candidate_count != len(self.candidates)
            or self.evaluated_candidate_count != len(self.candidates)
            or self.selected_candidate_id
            not in {item.candidate_id for item in self.candidates if item.admissible}
        ):
            raise RelationalSupportInvariantViolation(
                "candidate trace is incomplete or selected an inadmissible candidate"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_candidate_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "source_log_id": self.source_log_id,
            "program_registry_id": self.program_registry_id,
            "candidates": [item.to_document() for item in self.candidates],
            "selected_candidate_id": self.selected_candidate_id,
            "required_candidate_count": self.required_candidate_count,
            "evaluated_candidate_count": self.evaluated_candidate_count,
            "selection_rule": self.selection_rule,
            "candidate_subset_override": None,
        }

    @property
    def trace_id(self) -> str:
        return _content_id("candidate_trace", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "trace_id": self.trace_id}


def _candidate_selection_key(
    candidate: RelationalCoordinateCandidateV1,
    program_by_id: Mapping[str, RelationalCoordinateProgramV1],
) -> tuple[Any, ...]:
    programs = tuple(
        program_by_id[item]
        for item in (candidate.state_program_id, candidate.action_program_id)
        if item is not None
    )
    return (
        candidate.abstract_row_count,
        candidate.state_cell_count,
        -candidate.alias_pair_count,
        sum(item.node_count for item in programs),
        max((item.depth for item in programs), default=0),
        tuple(_program_complexity(item) for item in programs),
        candidate.state_program_id,
        candidate.action_program_id,
        candidate.candidate_id,
    )


def select_relational_coordinate_candidate_v1(
    source_log: SourceRelationalObservationLogV1,
    registry: RelationalProgramRegistryV1,
) -> RelationalCandidateTraceV1:
    """Exhaust the optional-single state/action coordinate product."""

    if (
        type(source_log) is not SourceRelationalObservationLogV1
        or type(registry) is not RelationalProgramRegistryV1
        or registry.source_log_id != source_log.log_id
    ):
        raise RelationalSupportInvariantViolation(
            "candidate selector source/registry binding mismatch"
        )
    state_programs = (None,) + _scalar_programs(registry, ProgramContext.STATE)
    action_programs = (None,) + _scalar_programs(
        registry,
        ProgramContext.STATE_ACTION,
    )
    rows = source_log.rows

    def raw_state_key(state: RawRelationalStateV1) -> tuple[Any, ...]:
        return (
            state.context_id,
            state.board,
            state.status,
            state.remaining_horizon,
        )

    catalogue_by_state_key: dict[
        tuple[Any, ...],
        tuple[RawRelationalActionV1, ...],
    ] = {}
    representative_by_state_key: dict[
        tuple[Any, ...],
        RawRelationalStateV1,
    ] = {}
    for row in rows:
        key = raw_state_key(row.state)
        prior = catalogue_by_state_key.get(key)
        if prior is not None and prior != row.legal_actions:
            raise RelationalSupportInvariantViolation(
                "source state has inconsistent action catalogues"
            )
        catalogue_by_state_key[key] = row.legal_actions
        representative_by_state_key[key] = row.state

    state_value_cache: dict[
        tuple[str | None, tuple[Any, ...]],
        tuple[str, Any],
    ] = {}
    action_value_cache: dict[
        tuple[str | None, int],
        tuple[str, Any],
    ] = {}
    behavior_cache: dict[
        tuple[str | None, int],
        tuple[tuple[tuple[Any, ...], int], ...],
    ] = {}

    def state_value(
        program: RelationalCoordinateProgramV1 | None,
        state: RawRelationalStateV1,
    ) -> tuple[str, Any]:
        semantic_state_key = raw_state_key(state)
        key = (
            None if program is None else program.program_id,
            semantic_state_key,
        )
        if key not in state_value_cache:
            state_value_cache[key] = (
                ("NULL", None)
                if program is None
                else _normalized_program_value(
                    program,
                    _eval_program(
                        program,
                        _EvaluationCovariate(
                            state,
                            None,
                            catalogue_by_state_key[semantic_state_key],
                        ),
                    ),
                )
            )
        return state_value_cache[key]

    for state_program in state_programs:
        state_program_id = None if state_program is None else state_program.program_id
        for row_index, row in enumerate(rows):
            masses: dict[tuple[Any, ...], Fraction] = {}
            for outcome in row.outcomes:
                if outcome.failure:
                    destination: tuple[Any, ...] = ("FAILURE",)
                elif outcome.next_state.remaining_horizon == 0:
                    destination = ("SAFE_TERMINAL",)
                else:
                    destination = (
                        "ACTIVE",
                        outcome.next_state.remaining_horizon,
                        state_value(state_program, outcome.next_state),
                    )
                masses[destination] = (
                    masses.get(destination, Fraction(0)) + outcome.probability
                )
            distribution = tuple(sorted(masses.items(), key=lambda item: repr(item[0])))
            behavior_cache[(state_program_id, row_index)] = (
                _ordinal_behavior_signature(distribution)
            )
    for action_program in action_programs:
        action_program_id = None if action_program is None else action_program.program_id
        for row_index, row in enumerate(rows):
            action_value_cache[(action_program_id, row_index)] = _action_value(
                action_program,
                row,
            )

    summaries: list[RelationalCoordinateCandidateV1] = []
    index = 0
    for state_program in state_programs:
        state_program_id = None if state_program is None else state_program.program_id
        state_values = {
            key: state_value(state_program, state)
            for key, state in representative_by_state_key.items()
        }
        for action_program in action_programs:
            action_program_id = (
                None if action_program is None else action_program.program_id
            )
            grouped: dict[
                tuple[Any, ...],
                list[SourceObservedGroundRowV1],
            ] = {}
            behavior_sets: dict[tuple[Any, ...], set[tuple[Any, ...]]] = {}
            state_members: dict[tuple[Any, ...], set[str]] = {}
            ground_action_sets: dict[
                tuple[Any, ...],
                set[tuple[str, Any]],
            ] = {}
            for row_index, row in enumerate(rows):
                semantic_state_key = raw_state_key(row.state)
                abstract_state_key = (
                    row.state.remaining_horizon,
                    state_values[semantic_state_key],
                )
                action_value = action_value_cache[
                    (action_program_id, row_index)
                ]
                key = abstract_state_key + (action_value,)
                grouped.setdefault(key, []).append(row)
                behavior_sets.setdefault(key, set()).add(
                    behavior_cache[(state_program_id, row_index)]
                )
                state_members.setdefault(abstract_state_key, set()).add(
                    semantic_state_key
                )
                ground_action_sets.setdefault(semantic_state_key, set()).add(
                    action_value
                )

            availability_by_signature: dict[
                tuple[Any, ...],
                set[tuple[tuple[str, Any], ...]],
            ] = {}
            for state_key, members in state_members.items():
                for state_id in members:
                    available = tuple(
                        sorted(ground_action_sets[state_id], key=repr)
                    )
                    availability_by_signature.setdefault(state_key, set()).add(available)
            availability_violations = sum(
                len(values) - 1
                for values in availability_by_signature.values()
                if len(values) > 1
            )
            contradictions = sum(
                len(values) - 1
                for values in behavior_sets.values()
                if len(values) > 1
            )
            alias_pairs = sum(
                len(rows) * (len(rows) - 1) // 2 for rows in grouped.values()
            )
            state_value_set = {
                value for _, value in state_values.values()
            }
            action_value_set = {
                action_value_cache[(action_program_id, row_index)]
                for row_index, _ in enumerate(rows)
                if action_program_id is not None
            }
            strict_state = (
                state_program is not None
                and 1 < len(state_value_set) < len(state_values)
            )
            strict_action = (
                action_program is not None
                and 1 < len(action_value_set) < len(source_log.rows)
            )
            summaries.append(
                RelationalCoordinateCandidateV1(
                    index,
                    state_program_id,
                    action_program_id,
                    len(rows),
                    len(grouped),
                    len(state_members),
                    alias_pairs,
                    contradictions,
                    availability_violations,
                    strict_state,
                    strict_action,
                    (
                        state_program is not None
                        and action_program is not None
                        and contradictions == 0
                        and availability_violations == 0
                        and strict_state
                        and strict_action
                    ),
                )
            )
            index += 1
    admissible = tuple(item for item in summaries if item.admissible)
    if not admissible:
        raise RelationalSupportInvariantViolation(
            "complete relational coordinate search found no admissible proposal"
        )
    program_by_id = {item.program_id: item for item in registry.programs}
    selected = min(
        admissible,
        key=lambda item: _candidate_selection_key(item, program_by_id),
    )
    return RelationalCandidateTraceV1(
        source_log.log_id,
        registry.registry_id,
        tuple(summaries),
        selected.candidate_id,
        len(summaries),
        len(summaries),
    )


@dataclass(frozen=True, slots=True)
class AnonymousSupportTemplateV1:
    remaining_horizon: int
    state_coordinate_value: tuple[str, Any]
    action_coordinate_value: tuple[str, Any]
    observed_source_row_count: int

    def __post_init__(self) -> None:
        if (
            type(self.remaining_horizon) is not int
            or not 1 <= self.remaining_horizon <= HORIZON
            or type(self.state_coordinate_value) is not tuple
            or type(self.action_coordinate_value) is not tuple
            or type(self.observed_source_row_count) is not int
            or self.observed_source_row_count <= 0
        ):
            raise RelationalSupportInvariantViolation(
                "anonymous support template is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.anonymous_relational_support_template.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate_value": list(self.state_coordinate_value),
            "action_coordinate_value": list(self.action_coordinate_value),
            "observed_source_row_count": self.observed_source_row_count,
        }

    @property
    def support_id(self) -> str:
        return _content_id("support", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "support_id": self.support_id}


@dataclass(frozen=True, slots=True)
class ProposedAbstractDecisionV1:
    remaining_horizon: int
    state_coordinate_value: tuple[str, Any]
    action_coordinate_value: tuple[str, Any]

    def __post_init__(self) -> None:
        if (
            type(self.remaining_horizon) is not int
            or not 1 <= self.remaining_horizon <= HORIZON
            or type(self.state_coordinate_value) is not tuple
            or type(self.action_coordinate_value) is not tuple
        ):
            raise RelationalSupportInvariantViolation(
                "proposed abstract decision is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate_value": list(self.state_coordinate_value),
            "action_coordinate_value": list(self.action_coordinate_value),
        }


@dataclass(frozen=True, slots=True)
class RelationalCoordinateSupportProposalV1:
    source_log_id: str
    program_registry: RelationalProgramRegistryV1
    candidate_trace: RelationalCandidateTraceV1
    state_program: RelationalCoordinateProgramV1
    action_program: RelationalCoordinateProgramV1
    support_templates: tuple[AnonymousSupportTemplateV1, ...]
    proposed_decisions: tuple[ProposedAbstractDecisionV1, ...]
    source_context_ids: tuple[str, ...]
    target_inputs_used: int = 0
    query_inputs_used: int = 0
    target_certificate_authority: bool = False
    exact_target_dynamics_claimed: bool = False
    concretizer_kind: str = (
        "uniform_over_distinct_matching_ground_actions_v1"
    )
    abstract_selector_randomized: bool = False

    def __post_init__(self) -> None:
        _cid(self.source_log_id, "proposal source log")
        if (
            type(self.program_registry) is not RelationalProgramRegistryV1
            or type(self.candidate_trace) is not RelationalCandidateTraceV1
            or type(self.state_program) is not RelationalCoordinateProgramV1
            or type(self.action_program) is not RelationalCoordinateProgramV1
        ):
            raise RelationalSupportInvariantViolation(
                "proposal rejects substituted construction objects"
            )
        _exact_tuple(
            self.support_templates,
            AnonymousSupportTemplateV1,
            "proposal support templates",
        )
        _exact_tuple(
            self.proposed_decisions,
            ProposedAbstractDecisionV1,
            "proposal decisions",
        )
        if (
            self.program_registry.source_log_id != self.source_log_id
            or self.candidate_trace.source_log_id != self.source_log_id
            or self.candidate_trace.program_registry_id
            != self.program_registry.registry_id
            or tuple(item.support_id for item in self.support_templates)
            != tuple(sorted({item.support_id for item in self.support_templates}))
            or self.source_context_ids
            != tuple(
                item.context_id
                for item in registered_relational_contexts_v1(ContextSplit.SOURCE)
            )
            or self.target_inputs_used != 0
            or self.query_inputs_used != 0
            or self.target_certificate_authority is not False
            or self.exact_target_dynamics_claimed is not False
            or self.concretizer_kind
            != "uniform_over_distinct_matching_ground_actions_v1"
            or self.abstract_selector_randomized is not False
        ):
            raise RelationalSupportInvariantViolation(
                "proposal source-only authority or ordering changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_coordinate_support_proposal.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_log_id": self.source_log_id,
            "program_registry": self.program_registry.to_document(),
            "candidate_trace": self.candidate_trace.to_document(),
            "state_program": self.state_program.to_document(),
            "action_program": self.action_program.to_document(),
            "support_templates": [
                item.to_document() for item in self.support_templates
            ],
            "proposed_decisions": [
                item.to_document() for item in self.proposed_decisions
            ],
            "source_context_ids": list(self.source_context_ids),
            "target_inputs_used": self.target_inputs_used,
            "query_inputs_used": self.query_inputs_used,
            "target_certificate_authority": self.target_certificate_authority,
            "exact_target_dynamics_claimed": self.exact_target_dynamics_claimed,
            "concretizer_kind": self.concretizer_kind,
            "abstract_selector_randomized": self.abstract_selector_randomized,
            "known_group_prior_used": False,
            "named_frontier_used": False,
        }

    @property
    def proposal_id(self) -> str:
        return _content_id("proposal", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "proposal_id": self.proposal_id}


def _abstract_distribution_for_row(
    row: SourceObservedGroundRowV1,
    state_program: RelationalCoordinateProgramV1,
    catalogue_by_state: Mapping[str, tuple[RawRelationalActionV1, ...]],
) -> tuple[tuple[tuple[Any, ...], Fraction], ...]:
    return _aggregate_source_destinations(row, state_program, catalogue_by_state)


def _derive_source_decisions(
    source_log: SourceRelationalObservationLogV1,
    state_program: RelationalCoordinateProgramV1,
    action_program: RelationalCoordinateProgramV1,
) -> tuple[ProposedAbstractDecisionV1, ...]:
    catalogue_by_state = _state_catalogues(source_log)
    decisions_by_context: list[dict[tuple[Any, ...], tuple[str, Any]]] = []
    for context in source_log.contexts:
        rows = tuple(
            item for item in source_log.rows if item.state.context_id == context.context_id
        )
        row_groups: dict[
            tuple[Any, ...],
            list[tuple[tuple[tuple[Any, ...], Fraction], ...]],
        ] = {}
        for row in rows:
            state_value = _state_value(
                state_program,
                row.state,
                row.legal_actions,
            )
            action_value = _action_value(action_program, row)
            key = (row.state.remaining_horizon, state_value, action_value)
            row_groups.setdefault(key, []).append(
                _abstract_distribution_for_row(
                    row,
                    state_program,
                    catalogue_by_state,
                )
            )
        distributions: dict[
            tuple[Any, ...],
            tuple[tuple[tuple[Any, ...], Fraction], ...],
        ] = {}
        for key, values in row_groups.items():
            if len(set(values)) != 1:
                raise RelationalSupportInvariantViolation(
                    "selected coordinate is not probability-representative inside a source context"
                )
            distributions[key] = values[0]

        available: dict[
            tuple[int, tuple[str, Any]],
            tuple[tuple[str, Any], ...],
        ] = {}
        for remaining, state_value, action_value in distributions:
            available.setdefault((remaining, state_value), ())
            available[(remaining, state_value)] = tuple(
                sorted(
                    set(available[(remaining, state_value)]) | {action_value},
                    key=repr,
                )
            )
        selected: dict[tuple[Any, ...], tuple[str, Any]] = {}
        continuation_survival: dict[tuple[Any, ...], Fraction] = {}
        for remaining in (1, 2):
            for state_key in sorted(
                (key for key in available if key[0] == remaining),
                key=repr,
            ):
                candidates: list[tuple[Fraction, tuple[str, Any]]] = []
                for action_value in available[state_key]:
                    distribution = distributions[state_key + (action_value,)]
                    survival = Fraction(0)
                    for destination, probability in distribution:
                        if destination[0] == "FAILURE":
                            value = Fraction(0)
                        elif destination[0] == "SAFE_TERMINAL":
                            value = Fraction(1)
                        else:
                            successor_key = (
                                destination[1],
                                destination[2],
                            )
                            value = continuation_survival[successor_key]
                        survival += probability * value
                    candidates.append((survival, action_value))
                best_survival = max(item[0] for item in candidates)
                best_action = min(
                    (item[1] for item in candidates if item[0] == best_survival),
                    key=repr,
                )
                selected[state_key] = best_action
                continuation_survival[state_key] = best_survival
        decisions_by_context.append(selected)
    first = decisions_by_context[0]
    if any(item != first for item in decisions_by_context[1:]):
        raise RelationalSupportInvariantViolation(
            "source contexts do not unanimously identify one abstract schedule"
        )
    return tuple(
        ProposedAbstractDecisionV1(remaining, state_value, action_value)
        for (remaining, state_value), action_value in sorted(first.items(), key=repr)
    )


def synthesize_relational_coordinate_support_v1(
    source_log: SourceRelationalObservationLogV1,
) -> RelationalCoordinateSupportProposalV1:
    """Source-only public producer: no kernel, target, query, or frontier input."""

    _validate_implementation_authority_v1()
    if type(source_log) is not SourceRelationalObservationLogV1:
        raise RelationalSupportInvariantViolation(
            "relational producer rejects substituted source logs"
        )
    registry = generate_relational_program_closure_v1(source_log)
    trace = select_relational_coordinate_candidate_v1(source_log, registry)
    selected = next(
        item
        for item in trace.candidates
        if item.candidate_id == trace.selected_candidate_id
    )
    by_id = {item.program_id: item for item in registry.programs}
    state_program = by_id[selected.state_program_id]
    action_program = by_id[selected.action_program_id]
    counts: dict[tuple[Any, ...], int] = {}
    for row in source_log.rows:
        key = (
            row.state.remaining_horizon,
            _state_value(state_program, row.state, row.legal_actions),
            _action_value(action_program, row),
        )
        counts[key] = counts.get(key, 0) + 1
    templates = tuple(
        sorted(
            (
                AnonymousSupportTemplateV1(
                    remaining,
                    state_value,
                    action_value,
                    count,
                )
                for (remaining, state_value, action_value), count in counts.items()
            ),
            key=lambda item: item.support_id,
        )
    )
    decisions = _derive_source_decisions(
        source_log,
        state_program,
        action_program,
    )
    return RelationalCoordinateSupportProposalV1(
        source_log.log_id,
        registry,
        trace,
        state_program,
        action_program,
        templates,
        decisions,
        tuple(item.context_id for item in source_log.contexts),
    )


@dataclass(frozen=True, slots=True)
class HeldOutRelationalOccurrenceV1:
    ordinal: int
    context_id: str
    context_key: str
    initial_board: tuple[int, ...]
    horizon: int = HORIZON
    risk_tolerance: Fraction = RISK_TOLERANCE
    held_out_from_source: bool = True

    def __post_init__(self) -> None:
        _cid(self.context_id, "held-out occurrence context")
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.context_key) is not str
            or type(self.initial_board) is not tuple
            or len(self.initial_board) != GRID_SIZE * GRID_SIZE
            or any(type(rank) is not int for rank in self.initial_board)
            or self.horizon != HORIZON
            or self.risk_tolerance != RISK_TOLERANCE
            or self.held_out_from_source is not True
        ):
            raise RelationalSupportInvariantViolation(
                "held-out occurrence is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.heldout_relational_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "ordinal": self.ordinal,
            "context_id": self.context_id,
            "context_key": self.context_key,
            "initial_board": list(self.initial_board),
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "held_out_from_source": self.held_out_from_source,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "occurrence_id": self.occurrence_id}


def _registered_occurrences(
    targets: tuple[RelationalStructuralContextV1, ...],
) -> tuple[HeldOutRelationalOccurrenceV1, ...]:
    result: list[HeldOutRelationalOccurrenceV1] = []
    for context in targets:
        states = _motif_states(context)
        for state in (states[0], states[-1]):
            result.append(
                HeldOutRelationalOccurrenceV1(
                    len(result),
                    context.context_id,
                    context.context_key,
                    state.board,
                )
            )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class RelationalFamilyPreregistrationV1:
    source_contexts: tuple[RelationalStructuralContextV1, ...]
    target_contexts: tuple[RelationalStructuralContextV1, ...]
    occurrences: tuple[HeldOutRelationalOccurrenceV1, ...]
    grammar_operations: tuple[str, ...] = _OPERATION_ORDER
    candidate_shape: str = "optional_single_state_x_optional_single_action_v1"
    prospective_source_log_absent: bool = True
    prospective_proposal_absent: bool = True
    prospective_target_evidence_absent: bool = True
    source_target_identity_disjoint: bool = True
    official_execution_allowed: bool = False
    implementation_sha256: str = IMPLEMENTATION_SHA256

    def __post_init__(self) -> None:
        _exact_tuple(
            self.source_contexts,
            RelationalStructuralContextV1,
            "preregistered source contexts",
        )
        _exact_tuple(
            self.target_contexts,
            RelationalStructuralContextV1,
            "preregistered target contexts",
        )
        _exact_tuple(
            self.occurrences,
            HeldOutRelationalOccurrenceV1,
            "preregistered occurrences",
        )
        _cid(self.implementation_sha256, "relational implementation")
        if (
            self.source_contexts
            != registered_relational_contexts_v1(ContextSplit.SOURCE)
            or self.target_contexts
            != registered_relational_contexts_v1(ContextSplit.TARGET)
            or self.occurrences != _registered_occurrences(self.target_contexts)
            or self.grammar_operations != _OPERATION_ORDER
            or self.candidate_shape
            != "optional_single_state_x_optional_single_action_v1"
            or self.prospective_source_log_absent is not True
            or self.prospective_proposal_absent is not True
            or self.prospective_target_evidence_absent is not True
            or self.source_target_identity_disjoint is not True
            or {
                item.structural_id for item in self.source_contexts
            }
            & {item.structural_id for item in self.target_contexts}
            or self.official_execution_allowed is not False
            or self.implementation_sha256 != IMPLEMENTATION_SHA256
        ):
            raise RelationalSupportInvariantViolation(
                "relational family preregistration changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_family_preregistration.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_contexts": [item.to_document() for item in self.source_contexts],
            "target_contexts": [item.to_document() for item in self.target_contexts],
            "occurrences": [item.to_document() for item in self.occurrences],
            "grammar_operations": list(self.grammar_operations),
            "candidate_shape": self.candidate_shape,
            "prospective_source_log_absent": self.prospective_source_log_absent,
            "prospective_proposal_absent": self.prospective_proposal_absent,
            "prospective_target_evidence_absent": (
                self.prospective_target_evidence_absent
            ),
            "source_target_identity_disjoint": self.source_target_identity_disjoint,
            "official_execution_allowed": self.official_execution_allowed,
            "implementation_sha256": self.implementation_sha256,
        }

    @property
    def preregistration_id(self) -> str:
        return _content_id("preregistration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "preregistration_id": self.preregistration_id}


def preregister_relational_support_family_v1() -> RelationalFamilyPreregistrationV1:
    _validate_implementation_authority_v1()
    source = registered_relational_contexts_v1(ContextSplit.SOURCE)
    target = registered_relational_contexts_v1(ContextSplit.TARGET)
    return RelationalFamilyPreregistrationV1(
        source,
        target,
        _registered_occurrences(target),
    )


def _ground_state(raw: RawRelationalStateV1) -> G2048State:
    try:
        status = G2048Status(raw.status)
    except ValueError as error:  # pragma: no cover - constructor already checks
        raise RelationalSupportInvariantViolation("raw state status changed") from error
    return G2048State(raw.board, status)


def _ground_action(raw: RawRelationalActionV1) -> G2048Action:
    return G2048Action(raw.first, raw.second, raw.survivor)


def _target_state_and_catalogue(
    context: RelationalStructuralContextV1,
    kernel: RankRelativeAcquisitionKernelV1,
    state: G2048State,
    remaining: int,
) -> tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]]:
    raw_state = _raw_state(context, state, remaining)
    catalogue = tuple(
        _raw_action(raw_state, action) for action in kernel.actions(state)
    )
    return raw_state, catalogue


def _target_coordinate_values(
    proposal: RelationalCoordinateSupportProposalV1,
    state: RawRelationalStateV1,
    catalogue: tuple[RawRelationalActionV1, ...],
    action: RawRelationalActionV1,
) -> tuple[tuple[str, Any], tuple[str, Any]]:
    state_value = _normalized_program_value(
        proposal.state_program,
        _eval_program(
            proposal.state_program,
            _EvaluationCovariate(state, None, catalogue),
        ),
    )
    action_value = _normalized_program_value(
        proposal.action_program,
        _eval_program(
            proposal.action_program,
            _EvaluationCovariate(state, action, catalogue),
        ),
    )
    return state_value, action_value


def _support_lookup(
    proposal: RelationalCoordinateSupportProposalV1,
) -> dict[tuple[Any, ...], AnonymousSupportTemplateV1]:
    return {
        (
            item.remaining_horizon,
            item.state_coordinate_value,
            item.action_coordinate_value,
        ): item
        for item in proposal.support_templates
    }


def _decision_lookup(
    proposal: RelationalCoordinateSupportProposalV1,
) -> dict[tuple[int, tuple[str, Any]], tuple[str, Any]]:
    return {
        (item.remaining_horizon, item.state_coordinate_value):
        item.action_coordinate_value
        for item in proposal.proposed_decisions
    }


def _selected_ground_actions(
    proposal: RelationalCoordinateSupportProposalV1,
    state: RawRelationalStateV1,
    catalogue: tuple[RawRelationalActionV1, ...],
    *,
    decision_override: Mapping[
        tuple[int, tuple[str, Any]],
        tuple[str, Any],
    ] | None = None,
) -> tuple[RawRelationalActionV1, ...]:
    state_value = _normalized_program_value(
        proposal.state_program,
        _eval_program(
            proposal.state_program,
            _EvaluationCovariate(state, None, catalogue),
        ),
    )
    decisions = (
        dict(decision_override)
        if decision_override is not None
        else _decision_lookup(proposal)
    )
    chosen = decisions.get((state.remaining_horizon, state_value))
    if chosen is None:
        return ()
    actions = tuple(
        action
        for action in catalogue
        if _normalized_program_value(
            proposal.action_program,
            _eval_program(
                proposal.action_program,
                _EvaluationCovariate(state, action, catalogue),
            ),
        )
        == chosen
    )
    return tuple(sorted(actions, key=lambda item: item.action_id))


class TargetAuditOutcome(str, Enum):
    FAILED_MISSING_SUPPORT = "FAILED_MISSING_SUPPORT"
    FAILED_RISK = "FAILED_RISK"
    FAILED_UNREGISTERED_SUPPORT = "FAILED_UNREGISTERED_SUPPORT"
    CERTIFIED = "CERTIFIED"


@dataclass(frozen=True, slots=True)
class TargetSupportIntervalV1:
    destination: tuple[Any, ...]
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        valid_destination = (
            type(self.destination) is tuple
            and (
                self.destination in (("FAILURE",), ("SAFE_TERMINAL",))
                or (
                    len(self.destination) == 3
                    and self.destination[0] == "ACTIVE"
                    and type(self.destination[1]) is int
                    and 0 <= self.destination[1] < HORIZON
                    and type(self.destination[2]) is tuple
                )
            )
        )
        if (
            not valid_destination
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
        ):
            raise RelationalSupportInvariantViolation(
                "target support interval is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_support_interval.v1",
            "schema_version": SCHEMA_VERSION,
            "destination": _jsonable(self.destination),
            "lower": _fdoc(self.lower),
            "upper": _fdoc(self.upper),
        }

    @property
    def interval_id(self) -> str:
        return _content_id("interval", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "interval_id": self.interval_id}


@dataclass(frozen=True, slots=True)
class PartialStatisticalSupportRowV1:
    support_template: AnonymousSupportTemplateV1
    evidence: str
    intervals: tuple[TargetSupportIntervalV1, ...]
    member_ground_row_ids: tuple[str, ...]
    normalized_reward: Fraction | None
    evidence_id: str | None

    def __post_init__(self) -> None:
        if type(self.support_template) is not AnonymousSupportTemplateV1:
            raise RelationalSupportInvariantViolation(
                "partial model row rejects substituted support"
            )
        _exact_tuple(self.intervals, TargetSupportIntervalV1, "row intervals")
        if type(self.member_ground_row_ids) is not tuple:
            raise RelationalSupportInvariantViolation("row member IDs are invalid")
        for item in self.member_ground_row_ids:
            _cid(item, "row member")
        if self.evidence == "MISSING":
            if (
                self.intervals
                or self.member_ground_row_ids
                or self.normalized_reward is not None
                or self.evidence_id is not None
            ):
                raise RelationalSupportInvariantViolation(
                    "missing support rows must remain vacuous"
                )
        elif self.evidence == "TARGET_RAW_STATISTICAL":
            if (
                len(self.intervals) != 2
                or not self.member_ground_row_ids
                or self.member_ground_row_ids
                != tuple(sorted(set(self.member_ground_row_ids)))
                or tuple(item.destination for item in self.intervals)
                != tuple(
                    sorted(
                        {item.destination for item in self.intervals},
                        key=repr,
                    )
                )
                or type(self.normalized_reward) is not Fraction
                or self.evidence_id is None
            ):
                raise RelationalSupportInvariantViolation(
                    "observed support row lacks statistical evidence"
                )
            _cid(self.evidence_id, "support-row evidence")
            if (
                sum((item.lower for item in self.intervals), Fraction(0)) > 1
                or sum((item.upper for item in self.intervals), Fraction(0)) < 1
                or any(
                    interval.destination[0] == "ACTIVE"
                    and interval.destination[1]
                    != self.support_template.remaining_horizon - 1
                    for interval in self.intervals
                )
            ):
                raise RelationalSupportInvariantViolation(
                    "support-row intervals violate simplex feasibility"
                )
        else:
            raise RelationalSupportInvariantViolation(
                "unknown support-row evidence kind"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.partial_statistical_support_row.v1",
            "schema_version": SCHEMA_VERSION,
            "support_template": self.support_template.to_document(),
            "evidence": self.evidence,
            "intervals": [item.to_document() for item in self.intervals],
            "member_ground_row_ids": list(self.member_ground_row_ids),
            "normalized_reward": (
                None
                if self.normalized_reward is None
                else _fdoc(self.normalized_reward)
            ),
            "evidence_id": self.evidence_id,
        }

    @property
    def model_row_id(self) -> str:
        return _content_id("model_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_row_id": self.model_row_id}


@dataclass(frozen=True, slots=True)
class RelationalPartialStatisticalModelV1:
    preregistration_id: str
    proposal_id: str
    context_id: str
    epoch_index: int
    rows: tuple[PartialStatisticalSupportRowV1, ...]
    target_evidence_ids: tuple[str, ...]
    source_dynamics_imported: bool = False
    exact_dynamics_claimed: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.preregistration_id, "model preregistration"),
            (self.proposal_id, "model proposal"),
            (self.context_id, "model context"),
        ):
            _cid(value, field)
        _exact_tuple(self.rows, PartialStatisticalSupportRowV1, "model rows")
        if (
            type(self.epoch_index) is not int
            or not 0 <= self.epoch_index <= 2
            or tuple(item.support_template.support_id for item in self.rows)
            != tuple(sorted({item.support_template.support_id for item in self.rows}))
            or type(self.target_evidence_ids) is not tuple
            or self.target_evidence_ids
            != tuple(sorted(set(self.target_evidence_ids)))
            or self.source_dynamics_imported is not False
            or self.exact_dynamics_claimed is not False
        ):
            raise RelationalSupportInvariantViolation(
                "partial statistical model identity or claim changed"
            )
        for item in self.target_evidence_ids:
            _cid(item, "model target evidence")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_partial_statistical_model.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "proposal_id": self.proposal_id,
            "context_id": self.context_id,
            "epoch_index": self.epoch_index,
            "rows": [item.to_document() for item in self.rows],
            "target_evidence_ids": list(self.target_evidence_ids),
            "source_dynamics_imported": self.source_dynamics_imported,
            "exact_dynamics_claimed": self.exact_dynamics_claimed,
            "statistical_coordinate_obligation_count": (
                self.statistical_coordinate_obligation_count
            ),
        }

    @property
    def statistical_coordinate_obligation_count(self) -> int:
        return sum(
            2 * len(item.member_ground_row_ids)
            for item in self.rows
            if item.evidence == "TARGET_RAW_STATISTICAL"
        )

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "model_id": self.model_id}


def initial_relational_partial_model_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
) -> RelationalPartialStatisticalModelV1:
    if (
        type(preregistration) is not RelationalFamilyPreregistrationV1
        or type(proposal) is not RelationalCoordinateSupportProposalV1
        or type(context) is not RelationalStructuralContextV1
        or context not in preregistration.target_contexts
    ):
        raise RelationalSupportInvariantViolation(
            "initial target model binding is invalid"
        )
    return RelationalPartialStatisticalModelV1(
        preregistration.preregistration_id,
        proposal.proposal_id,
        context.context_id,
        0,
        tuple(
            PartialStatisticalSupportRowV1(
                item,
                "MISSING",
                (),
                (),
                None,
                None,
            )
            for item in proposal.support_templates
        ),
        (),
    )


def _min_interval_expectation(
    intervals: tuple[TargetSupportIntervalV1, ...],
    values: Mapping[tuple[Any, ...], Fraction],
) -> Fraction:
    probabilities = {item.destination: item.lower for item in intervals}
    residual = 1 - sum(probabilities.values(), Fraction(0))
    if residual < 0:
        raise RelationalSupportInvariantViolation(
            "interval lower bounds exceed the simplex"
        )
    for item in sorted(intervals, key=lambda row: (values[row.destination], repr(row.destination))):
        room = item.upper - probabilities[item.destination]
        addition = min(room, residual)
        probabilities[item.destination] += addition
        residual -= addition
        if residual == 0:
            break
    if residual:
        raise RelationalSupportInvariantViolation(
            "interval upper bounds do not cover the simplex"
        )
    return sum(
        probabilities[destination] * values[destination]
        for destination in probabilities
    )


def _validate_initial_catalogues_v1(
    context: RelationalStructuralContextV1,
    initial_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
    occurrence: HeldOutRelationalOccurrenceV1 | None,
) -> None:
    if not initial_catalogues:
        raise RelationalSupportInvariantViolation(
            "model audit requires a nonempty initial catalogue"
        )
    for state, catalogue in initial_catalogues:
        if (
            type(state) is not RawRelationalStateV1
            or type(catalogue) is not tuple
            or state.context_id != context.context_id
            or state.status != G2048Status.ACTIVE.value
            or state.remaining_horizon != HORIZON
        ):
            raise RelationalSupportInvariantViolation(
                "initial target catalogue is malformed"
            )
        expected_actions: list[RawRelationalActionV1] = []
        for first, second in GRAPH_EDGES:
            if (
                state.board[first] != 0
                and state.board[first] == state.board[second]
            ):
                expected_actions.extend(
                    (
                        RawRelationalActionV1(
                            state.state_id,
                            min(first, second),
                            max(first, second),
                            first,
                        ),
                        RawRelationalActionV1(
                            state.state_id,
                            min(first, second),
                            max(first, second),
                            second,
                        ),
                    )
                )
        if catalogue != tuple(expected_actions):
            raise RelationalSupportInvariantViolation(
                "initial target action catalogue differs from graph semantics"
            )
    boards = tuple(state.board for state, _ in initial_catalogues)
    if occurrence is None:
        if (
            len(initial_catalogues) != 8
            or set(boards) != {state.board for state in _motif_states(context)}
        ):
            raise RelationalSupportInvariantViolation(
                "context audit must bind the complete incidence family"
            )
    elif (
        type(occurrence) is not HeldOutRelationalOccurrenceV1
        or occurrence.context_id != context.context_id
        or len(initial_catalogues) != 1
        or boards != (occurrence.initial_board,)
    ):
        raise RelationalSupportInvariantViolation(
            "occurrence audit initial catalogue is not identity-matched"
        )


def _audit_scope_id_v1(
    context: RelationalStructuralContextV1,
    initial_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
    occurrence: HeldOutRelationalOccurrenceV1 | None,
) -> str:
    records = sorted(
        (
            {
                "state": state.to_document(),
                "legal_actions": [
                    action.to_document() for action in catalogue
                ],
            }
            for state, catalogue in initial_catalogues
        ),
        key=lambda item: item["state"]["state_id"],
    )
    return _content_id(
        "audit_scope",
        {
            "schema": "acfqp.relational_model_audit_scope.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context.context_id,
            "scope_kind": (
                "REGISTERED_CONTEXT_FAMILY"
                if occurrence is None
                else "REGISTERED_POINT_OCCURRENCE"
            ),
            "occurrence_id": (
                None if occurrence is None else occurrence.occurrence_id
            ),
            "initial_catalogues": records,
        },
    )


@dataclass(frozen=True, slots=True)
class RelationalModelOnlyAuditV1:
    preregistration_id: str
    proposal_id: str
    context_id: str
    model_id: str
    evaluation_scope_id: str
    evaluation_scope_kind: str
    occurrence_id: str | None
    calibration_id: str
    family_confidence_lower: Fraction
    outcome: TargetAuditOutcome
    missing_support_ids: tuple[str, ...]
    survival_lower: Fraction
    failure_upper: Fraction
    normalized_reward_lower: Fraction
    normalized_regret_upper: Fraction
    target_transition_calls: int = 0
    source_dynamics_used: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.preregistration_id, "audit preregistration"),
            (self.proposal_id, "audit proposal"),
            (self.context_id, "audit context"),
            (self.model_id, "audit model"),
            (self.evaluation_scope_id, "audit evaluation scope"),
            (self.calibration_id, "audit calibration"),
        ):
            _cid(value, field)
        if (
            self.evaluation_scope_kind
            not in ("REGISTERED_CONTEXT_FAMILY", "REGISTERED_POINT_OCCURRENCE")
            or (
                self.evaluation_scope_kind == "REGISTERED_CONTEXT_FAMILY"
                and self.occurrence_id is not None
            )
            or (
                self.evaluation_scope_kind == "REGISTERED_POINT_OCCURRENCE"
                and self.occurrence_id is None
            )
            or (
                self.occurrence_id is not None
                and _cid(self.occurrence_id, "audit occurrence")
                != self.occurrence_id
            )
            or self.family_confidence_lower != Fraction(239, 250)
            or type(self.outcome) is not TargetAuditOutcome
            or type(self.missing_support_ids) is not tuple
            or self.missing_support_ids != tuple(sorted(set(self.missing_support_ids)))
            or any(
                type(value) is not Fraction or not 0 <= value <= 1
                for value in (
                    self.survival_lower,
                    self.failure_upper,
                    self.normalized_regret_upper,
                )
            )
            or type(self.normalized_reward_lower) is not Fraction
            or self.normalized_reward_lower < 0
            or self.failure_upper != 1 - self.survival_lower
            or self.target_transition_calls != 0
            or self.source_dynamics_used is not False
        ):
            raise RelationalSupportInvariantViolation(
                "model-only audit fields are inconsistent"
            )
        for item in self.missing_support_ids:
            _cid(item, "audit missing support")
        if self.outcome is TargetAuditOutcome.FAILED_MISSING_SUPPORT:
            if not self.missing_support_ids:
                raise RelationalSupportInvariantViolation(
                    "missing-support audit requires proof obligations"
                )
        elif self.missing_support_ids:
            raise RelationalSupportInvariantViolation(
                "non-missing audit cannot carry missing support"
            )
        if (
            self.outcome is TargetAuditOutcome.CERTIFIED
            and (
                self.failure_upper >= RISK_TOLERANCE
                or self.normalized_regret_upper != 0
            )
        ):
            raise RelationalSupportInvariantViolation(
                "certified audit does not satisfy risk/regret"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_model_only_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "proposal_id": self.proposal_id,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "evaluation_scope_id": self.evaluation_scope_id,
            "evaluation_scope_kind": self.evaluation_scope_kind,
            "occurrence_id": self.occurrence_id,
            "calibration_id": self.calibration_id,
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "outcome": self.outcome.value,
            "missing_support_ids": list(self.missing_support_ids),
            "survival_lower": _fdoc(self.survival_lower),
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_reward_lower": _fdoc(self.normalized_reward_lower),
            "normalized_regret_upper": _fdoc(self.normalized_regret_upper),
            "target_transition_calls": self.target_transition_calls,
            "source_dynamics_used": self.source_dynamics_used,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "audit_id": self.audit_id}


def audit_relational_partial_model_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    model: RelationalPartialStatisticalModelV1,
    calibration: RelationalHoeffdingCalibrationV1,
    initial_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
    *,
    occurrence: HeldOutRelationalOccurrenceV1 | None = None,
    decision_override: Mapping[
        tuple[int, tuple[str, Any]],
        tuple[str, Any],
    ] | None = None,
) -> RelationalModelOnlyAuditV1:
    """Audit only the partial model; no transition interface is accepted."""

    if (
        type(preregistration) is not RelationalFamilyPreregistrationV1
        or type(proposal) is not RelationalCoordinateSupportProposalV1
        or type(context) is not RelationalStructuralContextV1
        or type(model) is not RelationalPartialStatisticalModelV1
        or type(calibration) is not RelationalHoeffdingCalibrationV1
        or context not in preregistration.target_contexts
        or model.preregistration_id != preregistration.preregistration_id
        or model.proposal_id != proposal.proposal_id
        or model.context_id != context.context_id
        or type(initial_catalogues) is not tuple
        or calibration.coordinate_obligation_count != 176
        or model.statistical_coordinate_obligation_count
        > calibration.coordinate_obligation_count
        or (
            occurrence is not None
            and occurrence not in preregistration.occurrences
        )
    ):
        raise RelationalSupportInvariantViolation(
            "model-only audit binding is invalid"
        )
    _validate_initial_catalogues_v1(context, initial_catalogues, occurrence)
    evaluation_scope_id = _audit_scope_id_v1(
        context,
        initial_catalogues,
        occurrence,
    )
    support_by_key = _support_lookup(proposal)
    row_by_support = {
        item.support_template.support_id: item for item in model.rows
    }
    decisions = (
        dict(decision_override)
        if decision_override is not None
        else _decision_lookup(proposal)
    )
    missing: set[str] = set()
    unregistered = False
    memo: dict[tuple[int, tuple[str, Any]], tuple[Fraction, Fraction]] = {}

    def evaluate_state(
        remaining: int,
        state_value: tuple[str, Any],
    ) -> tuple[Fraction, Fraction]:
        nonlocal unregistered
        key = (remaining, state_value)
        if key in memo:
            return memo[key]
        action_value = decisions.get(key)
        if action_value is None:
            unregistered = True
            return Fraction(0), Fraction(0)
        support = support_by_key.get((remaining, state_value, action_value))
        if support is None:
            unregistered = True
            return Fraction(0), Fraction(0)
        row = row_by_support[support.support_id]
        if row.evidence == "MISSING":
            missing.add(support.support_id)
            return Fraction(0), Fraction(0)
        survival_values: dict[tuple[Any, ...], Fraction] = {}
        reward_values: dict[tuple[Any, ...], Fraction] = {}
        for interval in row.intervals:
            destination = interval.destination
            if destination[0] == "FAILURE":
                continuation_survival = Fraction(0)
                continuation_reward = Fraction(0)
            elif destination[0] == "SAFE_TERMINAL":
                continuation_survival = Fraction(1)
                continuation_reward = Fraction(0)
            elif destination[0] == "ACTIVE":
                continuation_survival, continuation_reward = evaluate_state(
                    destination[1],
                    destination[2],
                )
            else:
                raise RelationalSupportInvariantViolation(
                    "model row contains an unknown destination kind"
                )
            survival_values[destination] = continuation_survival
            reward_values[destination] = continuation_reward
        survival = _min_interval_expectation(row.intervals, survival_values)
        continuation_reward = _min_interval_expectation(
            row.intervals,
            reward_values,
        )
        reward = Fraction(row.normalized_reward) + continuation_reward
        memo[key] = (survival, reward)
        return memo[key]

    initial_values: list[tuple[Fraction, Fraction]] = []
    for state, catalogue in initial_catalogues:
        state_value = _normalized_program_value(
            proposal.state_program,
            _eval_program(
                proposal.state_program,
                _EvaluationCovariate(state, None, catalogue),
            ),
        )
        initial_values.append(evaluate_state(HORIZON, state_value))
    if unregistered:
        outcome = TargetAuditOutcome.FAILED_UNREGISTERED_SUPPORT
        survival = Fraction(0)
        reward = Fraction(0)
        regret = Fraction(1)
    elif missing:
        outcome = TargetAuditOutcome.FAILED_MISSING_SUPPORT
        survival = Fraction(0)
        reward = Fraction(0)
        regret = Fraction(1)
    else:
        survival = min(item[0] for item in initial_values)
        reward = min(item[1] for item in initial_values)
        # Every registered selected path performs the two deterministic merge
        # rewards.  The target-only rows establish both reward values.
        expected_reward = (
            Fraction(2 ** (context.low_rank + 1), 2 ** (RANK_CAP + 1))
            + Fraction(2 ** (context.low_rank + 2), 2 ** (RANK_CAP + 1))
        ) / NORMALIZER
        regret = max(Fraction(0), expected_reward - reward) / expected_reward
        outcome = (
            TargetAuditOutcome.CERTIFIED
            if 1 - survival < context.risk_tolerance and regret == 0
            else TargetAuditOutcome.FAILED_RISK
        )
    return RelationalModelOnlyAuditV1(
        preregistration.preregistration_id,
        proposal.proposal_id,
        context.context_id,
        model.model_id,
        evaluation_scope_id,
        (
            "REGISTERED_CONTEXT_FAMILY"
            if occurrence is None
            else "REGISTERED_POINT_OCCURRENCE"
        ),
        None if occurrence is None else occurrence.occurrence_id,
        calibration.calibration_id,
        calibration.family_confidence_lower,
        outcome,
        tuple(sorted(missing)),
        survival,
        1 - survival,
        reward,
        regret,
    )


@dataclass(frozen=True, slots=True)
class TargetRowAuthorizationV1:
    preregistration_id: str
    proposal_id: str
    context_id: str
    model_id: str
    failed_audit_id: str
    round_index: int
    authorized_support_ids: tuple[str, ...]
    target_transition_calls_before_authorization: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.preregistration_id, "authorization preregistration"),
            (self.proposal_id, "authorization proposal"),
            (self.context_id, "authorization context"),
            (self.model_id, "authorization model"),
            (self.failed_audit_id, "authorization audit"),
        ):
            _cid(value, field)
        if (
            self.round_index not in (1, 2)
            or type(self.authorized_support_ids) is not tuple
            or self.authorized_support_ids
            != tuple(sorted(set(self.authorized_support_ids)))
            or not self.authorized_support_ids
            or self.target_transition_calls_before_authorization != 0
        ):
            raise RelationalSupportInvariantViolation(
                "target row authorization is invalid"
            )
        for item in self.authorized_support_ids:
            _cid(item, "authorized support")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_row_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "proposal_id": self.proposal_id,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "failed_audit_id": self.failed_audit_id,
            "round_index": self.round_index,
            "authorized_support_ids": list(self.authorized_support_ids),
            "target_transition_calls_before_authorization": (
                self.target_transition_calls_before_authorization
            ),
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "authorization_id": self.authorization_id}


def authorize_failed_relational_support_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    model: RelationalPartialStatisticalModelV1,
    failed_audit: RelationalModelOnlyAuditV1,
    round_index: int,
) -> TargetRowAuthorizationV1:
    if (
        type(failed_audit) is not RelationalModelOnlyAuditV1
        or failed_audit.outcome is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
        or failed_audit.preregistration_id != preregistration.preregistration_id
        or failed_audit.proposal_id != proposal.proposal_id
        or failed_audit.context_id != context.context_id
        or failed_audit.model_id != model.model_id
        or round_index != model.epoch_index + 1
    ):
        raise RelationalSupportInvariantViolation(
            "only the current failed proof may authorize target rows"
        )
    return TargetRowAuthorizationV1(
        preregistration.preregistration_id,
        proposal.proposal_id,
        context.context_id,
        model.model_id,
        failed_audit.audit_id,
        round_index,
        failed_audit.missing_support_ids,
    )


@dataclass(frozen=True, slots=True)
class TargetOutcomeAtomV1:
    atom_index: int
    next_state: RawRelationalStateV1
    next_legal_actions: tuple[RawRelationalActionV1, ...]
    normalized_reward: Fraction
    failure: bool
    terminal: bool

    def __post_init__(self) -> None:
        _exact_tuple(
            self.next_legal_actions,
            RawRelationalActionV1,
            "target outcome next actions",
        )
        if (
            type(self.atom_index) is not int
            or not 0 <= self.atom_index < 16
            or type(self.next_state) is not RawRelationalStateV1
            or any(
                item.state_id != self.next_state.state_id
                for item in self.next_legal_actions
            )
            or type(self.normalized_reward) is not Fraction
            or self.normalized_reward < 0
            or type(self.failure) is not bool
            or type(self.terminal) is not bool
            or self.failure
            != (self.next_state.status == G2048Status.FAILURE.value)
            or self.terminal != self.failure
        ):
            raise RelationalSupportInvariantViolation(
                "target outcome atom is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_outcome_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "atom_index": self.atom_index,
            "next_state": self.next_state.to_document(),
            "next_legal_actions": [
                item.to_document() for item in self.next_legal_actions
            ],
            "normalized_reward": _fdoc(self.normalized_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "exact_probability": None,
            "support_authority": "registered_symbolic_outcome_support_v1",
        }

    @property
    def atom_id(self) -> str:
        return _content_id("outcome", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


@dataclass(frozen=True, slots=True)
class PackedSampledTargetGroundRowV1:
    context_id: str
    support_id: str
    authorization_id: str
    round_index: int
    state: RawRelationalStateV1
    action: RawRelationalActionV1
    legal_actions: tuple[RawRelationalActionV1, ...]
    outcome_atoms: tuple[TargetOutcomeAtomV1, ...]
    seed: str
    outcome_nibbles_hex: str
    sample_count: int = SAMPLE_COUNT_PER_GROUND_ROW
    exact_probabilities_absent: bool = True
    structural_outcome_support_known: bool = True
    unknown_outcome_support_claimed: bool = False
    probability_estimates_from_draws_only: bool = True

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "sampled row context"),
            (self.support_id, "sampled row support"),
            (self.authorization_id, "sampled row authorization"),
        ):
            _cid(value, field)
        _exact_tuple(self.legal_actions, RawRelationalActionV1, "sampled legal actions")
        _exact_tuple(self.outcome_atoms, TargetOutcomeAtomV1, "sampled outcome atoms")
        if (
            self.round_index not in (1, 2)
            or type(self.state) is not RawRelationalStateV1
            or type(self.action) is not RawRelationalActionV1
            or self.action not in self.legal_actions
            or self.action.state_id != self.state.state_id
            or tuple(item.atom_index for item in self.outcome_atoms)
            != tuple(range(len(self.outcome_atoms)))
            or not 1 <= len(self.outcome_atoms) <= 16
            or type(self.seed) is not str
            or not self.seed
            or type(self.outcome_nibbles_hex) is not str
            or len(self.outcome_nibbles_hex) != self.sample_count
            or any(
                character not in "0123456789abcdef"
                or int(character, 16) >= len(self.outcome_atoms)
                for character in self.outcome_nibbles_hex
            )
            or self.sample_count != SAMPLE_COUNT_PER_GROUND_ROW
            or self.exact_probabilities_absent is not True
            or self.structural_outcome_support_known is not True
            or self.unknown_outcome_support_claimed is not False
            or self.probability_estimates_from_draws_only is not True
        ):
            raise RelationalSupportInvariantViolation(
                "packed sampled target row is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.packed_sampled_target_ground_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "support_id": self.support_id,
            "authorization_id": self.authorization_id,
            "round_index": self.round_index,
            "state": self.state.to_document(),
            "action": self.action.to_document(),
            "legal_actions": [item.to_document() for item in self.legal_actions],
            "outcome_atoms": [item.to_document() for item in self.outcome_atoms],
            "seed": self.seed,
            "outcome_nibbles_hex": self.outcome_nibbles_hex,
            "sample_count": self.sample_count,
            "exact_probabilities_absent": self.exact_probabilities_absent,
            "structural_outcome_support_known": (
                self.structural_outcome_support_known
            ),
            "unknown_outcome_support_claimed": (
                self.unknown_outcome_support_claimed
            ),
            "probability_estimates_from_draws_only": (
                self.probability_estimates_from_draws_only
            ),
        }

    @property
    def sampled_row_id(self) -> str:
        return _content_id("sampled_row", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "sampled_row_id": self.sampled_row_id}


@dataclass(frozen=True, slots=True)
class TargetRelationalEvidenceV1:
    preregistration_id: str
    proposal_id: str
    context_id: str
    authorization_id: str
    round_index: int
    authorized_support_ids: tuple[str, ...]
    sampled_rows: tuple[PackedSampledTargetGroundRowV1, ...]
    ground_transition_row_count: int
    generative_sample_count: int
    source_rows_consumed_as_target_dynamics: int = 0

    def __post_init__(self) -> None:
        for value, field in (
            (self.preregistration_id, "evidence preregistration"),
            (self.proposal_id, "evidence proposal"),
            (self.context_id, "evidence context"),
            (self.authorization_id, "evidence authorization"),
        ):
            _cid(value, field)
        _exact_tuple(
            self.sampled_rows,
            PackedSampledTargetGroundRowV1,
            "target sampled rows",
        )
        if (
            self.round_index not in (1, 2)
            or self.authorized_support_ids
            != tuple(sorted(set(self.authorized_support_ids)))
            or not self.authorized_support_ids
            or not self.sampled_rows
            or tuple(item.sampled_row_id for item in self.sampled_rows)
            != tuple(sorted({item.sampled_row_id for item in self.sampled_rows}))
            or any(
                item.context_id != self.context_id
                or item.authorization_id != self.authorization_id
                or item.round_index != self.round_index
                or item.support_id not in self.authorized_support_ids
                for item in self.sampled_rows
            )
            or {
                item.support_id for item in self.sampled_rows
            }
            != set(self.authorized_support_ids)
            or self.ground_transition_row_count != len(self.sampled_rows)
            or self.generative_sample_count
            != len(self.sampled_rows) * SAMPLE_COUNT_PER_GROUND_ROW
            or self.source_rows_consumed_as_target_dynamics != 0
        ):
            raise RelationalSupportInvariantViolation(
                "target evidence coverage or accounting changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_relational_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "preregistration_id": self.preregistration_id,
            "proposal_id": self.proposal_id,
            "context_id": self.context_id,
            "authorization_id": self.authorization_id,
            "round_index": self.round_index,
            "authorized_support_ids": list(self.authorized_support_ids),
            "sampled_rows": [item.to_document() for item in self.sampled_rows],
            "ground_transition_row_count": self.ground_transition_row_count,
            "generative_sample_count": self.generative_sample_count,
            "source_rows_consumed_as_target_dynamics": (
                self.source_rows_consumed_as_target_dynamics
            ),
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "evidence_id": self.evidence_id}


def _counter_uniform_prefix(
    seed: str,
    context_id: str,
    support_id: str,
    state: RawRelationalStateV1,
    action: RawRelationalActionV1,
) -> bytes:
    payload = {
        "schema": "acfqp.relational_counter_uniform.v1",
        "seed": seed,
        "context_id": context_id,
        "support_id": support_id,
        "state": {
            "board": list(state.board),
            "status": state.status,
            "remaining_horizon": state.remaining_horizon,
        },
        "action": [action.first, action.second, action.survivor],
    }
    return (
        b"acfqp:relational-counter-uniform:v1\x00"
        + canonical_json_bytes(payload)
    )


def _counter_uint256_from_prefix(prefix: bytes, sample_index: int) -> int:
    if type(prefix) is not bytes or type(sample_index) is not int or sample_index < 0:
        raise RelationalSupportInvariantViolation("counter draw input is invalid")
    return int.from_bytes(
        hashlib.sha256(
            prefix + b"\x00" + sample_index.to_bytes(8, "big")
        ).digest(),
        "big",
    )
def _structural_target_outcome_atoms_v1(
    context: RelationalStructuralContextV1,
    kernel: RankRelativeAcquisitionKernelV1,
    state: RawRelationalStateV1,
    action: RawRelationalActionV1,
) -> tuple[TargetOutcomeAtomV1, ...]:
    """Enumerate registered symbolic support without reading probabilities."""

    ground_state = _ground_state(state)
    ground_action = _ground_action(action)
    if ground_action not in kernel.actions(ground_state):
        raise RelationalSupportInvariantViolation(
            "target symbolic-support action is not legal"
        )
    rank = ground_state.board[ground_action.first]
    board_after_merge = list(ground_state.board)
    board_after_merge[ground_action.first] = 0
    board_after_merge[ground_action.second] = 0
    board_after_merge[ground_action.survivor] = min(rank + 1, kernel.rank_cap)
    empty_cells = tuple(
        index
        for index, value in enumerate(board_after_merge)
        if value == 0
    )
    reward = Fraction(2 ** (rank + 1), 2 ** (kernel.rank_cap + 1))
    atoms: list[TargetOutcomeAtomV1] = []
    for cell in empty_cells:
        for spawn_rank in (context.low_rank, context.high_rank):
            next_board = board_after_merge.copy()
            next_board[cell] = spawn_rank
            provisional = G2048State(tuple(next_board))
            failed = not kernel.actions(provisional)
            next_state = G2048State(
                provisional.board,
                G2048Status.FAILURE if failed else G2048Status.ACTIVE,
            )
            raw_next, next_catalogue = _target_state_and_catalogue(
                context,
                kernel,
                next_state,
                state.remaining_horizon - 1,
            )
            atoms.append(
                TargetOutcomeAtomV1(
                    len(atoms),
                    raw_next,
                    next_catalogue,
                    reward / NORMALIZER,
                    failed,
                    failed,
                )
            )
    return tuple(atoms)


def _sample_target_row(
    context: RelationalStructuralContextV1,
    kernel: RankRelativeAcquisitionKernelV1,
    proposal: RelationalCoordinateSupportProposalV1,
    authorization: TargetRowAuthorizationV1,
    state: RawRelationalStateV1,
    catalogue: tuple[RawRelationalActionV1, ...],
    action: RawRelationalActionV1,
    support: AnonymousSupportTemplateV1,
) -> PackedSampledTargetGroundRowV1:
    atoms = _structural_target_outcome_atoms_v1(
        context,
        kernel,
        state,
        action,
    )
    seed = (
        f"acfqp-v0064-target-{context.context_key}-round-"
        f"{authorization.round_index}-v1"
    )
    uniform_prefix = _counter_uniform_prefix(
        seed,
        context.context_id,
        support.support_id,
        state,
        action,
    )
    empty_cell_count = len(atoms) // 2
    draw_indices = [
        kernel.sample_structural_atom_index(
            empty_cell_count,
            _counter_uint256_from_prefix(uniform_prefix, sample_index),
        )
        for sample_index in range(SAMPLE_COUNT_PER_GROUND_ROW)
    ]
    draws = "".join(format(index, "x") for index in draw_indices)
    return PackedSampledTargetGroundRowV1(
        context.context_id,
        support.support_id,
        authorization.authorization_id,
        authorization.round_index,
        state,
        action,
        catalogue,
        atoms,
        seed,
        draws,
    )


def acquire_authorized_target_rows_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    authorization: TargetRowAuthorizationV1,
    acquisition_kernel: RankRelativeAcquisitionKernelV1,
    state_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
) -> TargetRelationalEvidenceV1:
    """Use the exact kernel only behind an already-frozen authorization."""

    if (
        type(acquisition_kernel) is not RankRelativeAcquisitionKernelV1
        or acquisition_kernel.context_key != context.context_key
        or acquisition_kernel.low_rank != context.low_rank
        or acquisition_kernel.low_rank_probability != context.low_rank_probability
        or authorization.preregistration_id != preregistration.preregistration_id
        or authorization.proposal_id != proposal.proposal_id
        or authorization.context_id != context.context_id
        or type(state_catalogues) is not tuple
    ):
        raise RelationalSupportInvariantViolation(
            "target acquisition authority binding is invalid"
        )
    support_by_key = _support_lookup(proposal)
    authorized = set(authorization.authorized_support_ids)
    rows: dict[str, PackedSampledTargetGroundRowV1] = {}
    for state, catalogue in state_catalogues:
        if state.context_id != context.context_id:
            raise RelationalSupportInvariantViolation(
                "target acquisition received a foreign state"
            )
        for action in catalogue:
            state_value, action_value = _target_coordinate_values(
                proposal,
                state,
                catalogue,
                action,
            )
            support = support_by_key.get(
                (state.remaining_horizon, state_value, action_value)
            )
            if support is None or support.support_id not in authorized:
                continue
            row = _sample_target_row(
                context,
                acquisition_kernel,
                proposal,
                authorization,
                state,
                catalogue,
                action,
                support,
            )
            rows[row.sampled_row_id] = row
    result = tuple(sorted(rows.values(), key=lambda item: item.sampled_row_id))
    if {item.support_id for item in result} != authorized:
        raise RelationalSupportInvariantViolation(
            "authorized target support was not materialized completely"
        )
    return TargetRelationalEvidenceV1(
        preregistration.preregistration_id,
        proposal.proposal_id,
        context.context_id,
        authorization.authorization_id,
        authorization.round_index,
        authorization.authorized_support_ids,
        result,
        len(result),
        len(result) * SAMPLE_COUNT_PER_GROUND_ROW,
    )


@dataclass(frozen=True, slots=True)
class TargetEvidenceVerificationV1:
    evidence_id: str
    authorization_id: str
    failed_audit_id: str
    model_id: str
    context_id: str
    replayed_ground_row_count: int
    replayed_generative_sample_count: int
    canonical_seed_verified: bool
    legal_catalogues_verified: bool
    symbolic_support_verified: bool
    raw_draws_replayed: bool
    verifier_kind: str = "same_implementation_semantic_replay_v1"

    def __post_init__(self) -> None:
        for value, field in (
            (self.evidence_id, "verified evidence"),
            (self.authorization_id, "verified authorization"),
            (self.failed_audit_id, "verified failed audit"),
            (self.model_id, "verified model"),
            (self.context_id, "verified context"),
        ):
            _cid(value, field)
        if (
            type(self.replayed_ground_row_count) is not int
            or self.replayed_ground_row_count <= 0
            or self.replayed_generative_sample_count
            != self.replayed_ground_row_count
            * SAMPLE_COUNT_PER_GROUND_ROW
            or self.canonical_seed_verified is not True
            or self.legal_catalogues_verified is not True
            or self.symbolic_support_verified is not True
            or self.raw_draws_replayed is not True
            or self.verifier_kind
            != "same_implementation_semantic_replay_v1"
        ):
            raise RelationalSupportInvariantViolation(
                "target evidence verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.target_evidence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "evidence_id": self.evidence_id,
            "authorization_id": self.authorization_id,
            "failed_audit_id": self.failed_audit_id,
            "model_id": self.model_id,
            "context_id": self.context_id,
            "replayed_ground_row_count": self.replayed_ground_row_count,
            "replayed_generative_sample_count": (
                self.replayed_generative_sample_count
            ),
            "canonical_seed_verified": self.canonical_seed_verified,
            "legal_catalogues_verified": self.legal_catalogues_verified,
            "symbolic_support_verified": self.symbolic_support_verified,
            "raw_draws_replayed": self.raw_draws_replayed,
            "verifier_kind": self.verifier_kind,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("evidence_verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_target_relational_evidence_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    model: RelationalPartialStatisticalModelV1,
    failed_audit: RelationalModelOnlyAuditV1,
    authorization: TargetRowAuthorizationV1,
    evidence: TargetRelationalEvidenceV1,
    acquisition_kernel: RankRelativeAcquisitionKernelV1,
    state_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
) -> TargetEvidenceVerificationV1:
    expected_authorization = authorize_failed_relational_support_v1(
        preregistration,
        proposal,
        context,
        model,
        failed_audit,
        authorization.round_index,
    )
    if authorization.to_document() != expected_authorization.to_document():
        raise RelationalSupportInvariantViolation(
            "target evidence authorization lineage failed replay"
        )
    expected_evidence = acquire_authorized_target_rows_v1(
        preregistration,
        proposal,
        context,
        authorization,
        acquisition_kernel,
        state_catalogues,
    )
    _runtime_shape(evidence, expected_evidence, "target evidence")
    if evidence.to_document() != expected_evidence.to_document():
        raise RelationalSupportInvariantViolation(
            "target evidence seed, catalogue, support, or raw draws failed replay"
        )
    return TargetEvidenceVerificationV1(
        evidence.evidence_id,
        authorization.authorization_id,
        failed_audit.audit_id,
        model.model_id,
        context.context_id,
        evidence.ground_transition_row_count,
        evidence.generative_sample_count,
        True,
        True,
        True,
        True,
    )


def successor_catalogues_from_evidence_v1(
    evidence: TargetRelationalEvidenceV1,
) -> tuple[
    tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
    ...,
]:
    result: dict[
        tuple[Any, ...],
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
    ] = {}
    for row in evidence.sampled_rows:
        for atom in row.outcome_atoms:
            if atom.failure or atom.terminal or atom.next_state.remaining_horizon == 0:
                continue
            key = (
                atom.next_state.context_id,
                atom.next_state.board,
                atom.next_state.status,
                atom.next_state.remaining_horizon,
            )
            prior = result.get(key)
            value = (atom.next_state, atom.next_legal_actions)
            if prior is not None and prior != value:
                raise RelationalSupportInvariantViolation(
                    "observed successor catalogue is inconsistent"
                )
            result[key] = value
    return tuple(sorted(result.values(), key=lambda item: item[0].state_id))


def _atom_destination(
    proposal: RelationalCoordinateSupportProposalV1,
    atom: TargetOutcomeAtomV1,
) -> tuple[Any, ...]:
    if atom.failure:
        return ("FAILURE",)
    if atom.next_state.remaining_horizon == 0:
        return ("SAFE_TERMINAL",)
    state_value = _normalized_program_value(
        proposal.state_program,
        _eval_program(
            proposal.state_program,
            _EvaluationCovariate(
                atom.next_state,
                None,
                atom.next_legal_actions,
            ),
        ),
    )
    return ("ACTIVE", atom.next_state.remaining_horizon, state_value)


def build_relational_partial_model_v1(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    evidences: tuple[TargetRelationalEvidenceV1, ...],
    evidence_verifications: tuple[TargetEvidenceVerificationV1, ...],
) -> RelationalPartialStatisticalModelV1:
    if (
        type(evidences) is not tuple
        or type(evidence_verifications) is not tuple
        or len(evidences) not in (1, 2)
        or len(evidence_verifications) != len(evidences)
        or tuple(item.round_index for item in evidences)
        != tuple(range(1, len(evidences) + 1))
        or tuple(item.evidence_id for item in evidence_verifications)
        != tuple(item.evidence_id for item in evidences)
        or any(
            item.preregistration_id != preregistration.preregistration_id
            or item.proposal_id != proposal.proposal_id
            or item.context_id != context.context_id
            for item in evidences
        )
        or any(
            type(item) is not TargetEvidenceVerificationV1
            or item.context_id != context.context_id
            for item in evidence_verifications
        )
    ):
        raise RelationalSupportInvariantViolation(
            "partial model evidence history is invalid"
        )
    evidence_by_support: dict[str, TargetRelationalEvidenceV1] = {}
    rows_by_support: dict[str, list[PackedSampledTargetGroundRowV1]] = {}
    for evidence in evidences:
        for support_id in evidence.authorized_support_ids:
            if support_id in evidence_by_support:
                raise RelationalSupportInvariantViolation(
                    "target support was acquired twice"
                )
            evidence_by_support[support_id] = evidence
        for row in evidence.sampled_rows:
            rows_by_support.setdefault(row.support_id, []).append(row)

    model_rows: list[PartialStatisticalSupportRowV1] = []
    for support in proposal.support_templates:
        members = rows_by_support.get(support.support_id)
        if not members:
            model_rows.append(
                PartialStatisticalSupportRowV1(
                    support,
                    "MISSING",
                    (),
                    (),
                    None,
                    None,
                )
            )
            continue
        member_bounds: list[
            dict[tuple[Any, ...], tuple[Fraction, Fraction]]
        ] = []
        rewards: set[Fraction] = set()
        all_destinations: set[tuple[Any, ...]] = set()
        for row in members:
            destinations = tuple(
                _atom_destination(proposal, atom) for atom in row.outcome_atoms
            )
            structural_support = set(destinations)
            counts: dict[tuple[Any, ...], int] = {}
            for character in row.outcome_nibbles_hex:
                destination = destinations[int(character, 16)]
                counts[destination] = counts.get(destination, 0) + 1
            bounds: dict[tuple[Any, ...], tuple[Fraction, Fraction]] = {}
            for destination in structural_support:
                empirical = Fraction(
                    counts.get(destination, 0),
                    SAMPLE_COUNT_PER_GROUND_ROW,
                )
                bounds[destination] = (
                    max(Fraction(0), empirical - HOEFFDING_RADIUS),
                    min(Fraction(1), empirical + HOEFFDING_RADIUS),
                )
            member_bounds.append(bounds)
            all_destinations.update(structural_support)
            rewards.update(atom.normalized_reward for atom in row.outcome_atoms)
        if len(rewards) != 1:
            raise RelationalSupportInvariantViolation(
                "one anonymous support row has inconsistent observed rewards"
            )
        intervals = tuple(
            TargetSupportIntervalV1(
                destination,
                min(
                    bounds.get(destination, (Fraction(0), Fraction(0)))[0]
                    for bounds in member_bounds
                ),
                max(
                    bounds.get(destination, (Fraction(0), Fraction(0)))[1]
                    for bounds in member_bounds
                ),
            )
            for destination in sorted(all_destinations, key=repr)
        )
        evidence = evidence_by_support[support.support_id]
        model_rows.append(
            PartialStatisticalSupportRowV1(
                support,
                "TARGET_RAW_STATISTICAL",
                intervals,
                tuple(sorted(item.sampled_row_id for item in members)),
                next(iter(rewards)),
                evidence.evidence_id,
            )
        )
    return RelationalPartialStatisticalModelV1(
        preregistration.preregistration_id,
        proposal.proposal_id,
        context.context_id,
        len(evidences),
        tuple(
            sorted(
                model_rows,
                key=lambda item: item.support_template.support_id,
            )
        ),
        tuple(sorted(item.evidence_id for item in evidences)),
    )


@dataclass(frozen=True, slots=True)
class ColdDirectGroundControlV1:
    occurrence_id: str
    context_id: str
    reachable_state_action_row_count: int
    exact_kernel_row_enumerations: int
    composed_candidate_count: int
    selected_failure_probability: Fraction
    selected_normalized_reward: Fraction
    feasible: bool
    model_reuse_count: int = 0

    def __post_init__(self) -> None:
        _cid(self.occurrence_id, "direct occurrence")
        _cid(self.context_id, "direct context")
        if (
            self.reachable_state_action_row_count != 18
            or self.exact_kernel_row_enumerations != 18
            or self.composed_candidate_count != 22
            or type(self.selected_failure_probability) is not Fraction
            or type(self.selected_normalized_reward) is not Fraction
            or type(self.feasible) is not bool
            or self.feasible
            != (self.selected_failure_probability <= RISK_TOLERANCE)
            or self.model_reuse_count != 0
        ):
            raise RelationalSupportInvariantViolation(
                "cold direct-ground control changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.cold_direct_ground_control.v1",
            "schema_version": SCHEMA_VERSION,
            "occurrence_id": self.occurrence_id,
            "context_id": self.context_id,
            "reachable_state_action_row_count": (
                self.reachable_state_action_row_count
            ),
            "exact_kernel_row_enumerations": self.exact_kernel_row_enumerations,
            "composed_candidate_count": self.composed_candidate_count,
            "selected_failure_probability": _fdoc(
                self.selected_failure_probability
            ),
            "selected_normalized_reward": _fdoc(
                self.selected_normalized_reward
            ),
            "feasible": self.feasible,
            "model_reuse_count": self.model_reuse_count,
            "statistical_draw_comparison_claimed": False,
        }

    @property
    def direct_control_id(self) -> str:
        return _content_id("direct", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "direct_control_id": self.direct_control_id}


def _cold_direct_ground_control(
    occurrence: HeldOutRelationalOccurrenceV1,
    context: RelationalStructuralContextV1,
) -> ColdDirectGroundControlV1:
    kernel = _kernel_for_context(context)
    state = G2048State(occurrence.initial_board)
    query = QuerySpec(
        ((Fraction(1), state),),
        HORIZON,
        (("merge", Fraction(1)),),
        "default",
        RISK_TOLERANCE,
        NORMALIZER,
    )
    result = solve_ground_pareto(kernel, query)
    if result.selected is None:
        raise RelationalSupportInvariantViolation(
            "registered held-out direct query became infeasible"
        )
    row_count = sum(
        len(kernel.actions(reachable_state))
        for _, reachable_state in reachable_decision_pairs(kernel, query)
    )
    return ColdDirectGroundControlV1(
        occurrence.occurrence_id,
        context.context_id,
        row_count,
        row_count,
        result.composed_candidate_count,
        result.selected.failure_probability,
        result.selected.expected_reward,
        result.selected is not None,
    )


@dataclass(frozen=True, slots=True)
class RelationalTargetContextResultV1:
    context: RelationalStructuralContextV1
    initial_model: RelationalPartialStatisticalModelV1
    first_audit: RelationalModelOnlyAuditV1
    first_authorization: TargetRowAuthorizationV1
    first_evidence: TargetRelationalEvidenceV1
    first_evidence_verification: TargetEvidenceVerificationV1
    intermediate_model: RelationalPartialStatisticalModelV1
    second_audit: RelationalModelOnlyAuditV1
    second_authorization: TargetRowAuthorizationV1
    second_evidence: TargetRelationalEvidenceV1
    second_evidence_verification: TargetEvidenceVerificationV1
    final_model: RelationalPartialStatisticalModelV1
    final_audit: RelationalModelOnlyAuditV1
    occurrence_audits: tuple[RelationalModelOnlyAuditV1, ...]
    direct_controls: tuple[ColdDirectGroundControlV1, ...]
    context_build_ground_rows: int
    occurrence_new_ground_rows: tuple[int, ...]

    def __post_init__(self) -> None:
        if (
            type(self.context) is not RelationalStructuralContextV1
            or type(self.initial_model) is not RelationalPartialStatisticalModelV1
            or type(self.first_audit) is not RelationalModelOnlyAuditV1
            or type(self.first_authorization) is not TargetRowAuthorizationV1
            or type(self.first_evidence) is not TargetRelationalEvidenceV1
            or type(self.first_evidence_verification)
            is not TargetEvidenceVerificationV1
            or type(self.intermediate_model) is not RelationalPartialStatisticalModelV1
            or type(self.second_audit) is not RelationalModelOnlyAuditV1
            or type(self.second_authorization) is not TargetRowAuthorizationV1
            or type(self.second_evidence) is not TargetRelationalEvidenceV1
            or type(self.second_evidence_verification)
            is not TargetEvidenceVerificationV1
            or type(self.final_model) is not RelationalPartialStatisticalModelV1
            or type(self.final_audit) is not RelationalModelOnlyAuditV1
        ):
            raise RelationalSupportInvariantViolation(
                "context result rejects substituted chain objects"
            )
        _exact_tuple(
            self.occurrence_audits,
            RelationalModelOnlyAuditV1,
            "context occurrence audits",
        )
        _exact_tuple(
            self.direct_controls,
            ColdDirectGroundControlV1,
            "context direct controls",
        )
        if (
            self.initial_model.context_id != self.context.context_id
            or self.initial_model.epoch_index != 0
            or self.first_audit.model_id != self.initial_model.model_id
            or self.first_audit.evaluation_scope_kind
            != "REGISTERED_CONTEXT_FAMILY"
            or self.first_audit.outcome
            is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
            or len(self.first_audit.missing_support_ids) != 1
            or self.first_authorization.authorized_support_ids
            != self.first_audit.missing_support_ids
            or self.first_authorization.model_id != self.initial_model.model_id
            or self.first_authorization.failed_audit_id
            != self.first_audit.audit_id
            or self.first_evidence.authorization_id
            != self.first_authorization.authorization_id
            or self.first_evidence_verification.evidence_id
            != self.first_evidence.evidence_id
            or self.first_evidence_verification.authorization_id
            != self.first_authorization.authorization_id
            or self.first_evidence_verification.failed_audit_id
            != self.first_audit.audit_id
            or self.first_evidence_verification.model_id
            != self.initial_model.model_id
            or self.first_evidence.ground_transition_row_count != 8
            or self.intermediate_model.epoch_index != 1
            or self.intermediate_model.target_evidence_ids
            != (self.first_evidence.evidence_id,)
            or self.second_audit.model_id != self.intermediate_model.model_id
            or self.second_audit.evaluation_scope_id
            != self.first_audit.evaluation_scope_id
            or self.second_audit.outcome
            is not TargetAuditOutcome.FAILED_MISSING_SUPPORT
            or len(self.second_audit.missing_support_ids) != 2
            or self.second_authorization.authorized_support_ids
            != self.second_audit.missing_support_ids
            or self.second_authorization.model_id
            != self.intermediate_model.model_id
            or self.second_authorization.failed_audit_id
            != self.second_audit.audit_id
            or self.second_evidence.authorization_id
            != self.second_authorization.authorization_id
            or self.second_evidence_verification.evidence_id
            != self.second_evidence.evidence_id
            or self.second_evidence_verification.authorization_id
            != self.second_authorization.authorization_id
            or self.second_evidence_verification.failed_audit_id
            != self.second_audit.audit_id
            or self.second_evidence_verification.model_id
            != self.intermediate_model.model_id
            or self.second_evidence.ground_transition_row_count != 16
            or self.final_model.epoch_index != 2
            or set(self.final_model.target_evidence_ids)
            != {
                self.first_evidence.evidence_id,
                self.second_evidence.evidence_id,
            }
            or self.final_audit.model_id != self.final_model.model_id
            or self.final_audit.evaluation_scope_id
            != self.first_audit.evaluation_scope_id
            or len(
                {
                    self.first_audit.calibration_id,
                    self.second_audit.calibration_id,
                    self.final_audit.calibration_id,
                    *(item.calibration_id for item in self.occurrence_audits),
                }
            )
            != 1
            or self.final_audit.outcome is not TargetAuditOutcome.CERTIFIED
            or len(self.occurrence_audits) != 2
            or any(
                item.outcome is not TargetAuditOutcome.CERTIFIED
                or item.model_id != self.final_model.model_id
                for item in self.occurrence_audits
            )
            or tuple(item.occurrence_id for item in self.occurrence_audits)
            != tuple(item.occurrence_id for item in self.direct_controls)
            or len(set(item.audit_id for item in self.occurrence_audits)) != 2
            or len(self.direct_controls) != 2
            or any(
                item.context_id != self.context.context_id
                for item in self.direct_controls
            )
            or self.context_build_ground_rows != 24
            or self.occurrence_new_ground_rows != (0, 0)
        ):
            raise RelationalSupportInvariantViolation(
                "target context chronology, recovery, or reuse changed"
            )

    @property
    def target_ground_row_count(self) -> int:
        return (
            self.first_evidence.ground_transition_row_count
            + self.second_evidence.ground_transition_row_count
        )

    @property
    def target_sample_count(self) -> int:
        return (
            self.first_evidence.generative_sample_count
            + self.second_evidence.generative_sample_count
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_target_context_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context": self.context.to_document(),
            "initial_model_id": self.initial_model.model_id,
            "first_audit_id": self.first_audit.audit_id,
            "first_authorization_id": self.first_authorization.authorization_id,
            "first_evidence_id": self.first_evidence.evidence_id,
            "first_evidence_verification_id": (
                self.first_evidence_verification.verification_id
            ),
            "intermediate_model_id": self.intermediate_model.model_id,
            "second_audit_id": self.second_audit.audit_id,
            "second_authorization_id": self.second_authorization.authorization_id,
            "second_evidence_id": self.second_evidence.evidence_id,
            "second_evidence_verification_id": (
                self.second_evidence_verification.verification_id
            ),
            "final_model_id": self.final_model.model_id,
            "final_audit_id": self.final_audit.audit_id,
            "occurrence_audit_ids": [
                item.audit_id for item in self.occurrence_audits
            ],
            "direct_control_ids": [
                item.direct_control_id for item in self.direct_controls
            ],
            "target_ground_row_count": self.target_ground_row_count,
            "target_sample_count": self.target_sample_count,
            "context_build_ground_rows": self.context_build_ground_rows,
            "occurrence_new_ground_rows": list(
                self.occurrence_new_ground_rows
            ),
            "occurrence_reuse_semantics": (
                "post_context_build_query_only_reuse_v1"
            ),
        }

    @property
    def context_result_id(self) -> str:
        return _content_id("context_result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_result_id": self.context_result_id}


def _initial_target_catalogues(
    context: RelationalStructuralContextV1,
    kernel: RankRelativeAcquisitionKernelV1,
) -> tuple[
    tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
    ...,
]:
    return tuple(
        _target_state_and_catalogue(context, kernel, state, HORIZON)
        for state in _motif_states(context)
    )


def _run_target_context(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    calibration: RelationalHoeffdingCalibrationV1,
) -> RelationalTargetContextResultV1:
    kernel = _kernel_for_context(context)
    initial_catalogues = _initial_target_catalogues(context, kernel)
    initial_model = initial_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
    )
    first_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        calibration,
        initial_catalogues,
    )
    first_authorization = authorize_failed_relational_support_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        first_audit,
        1,
    )
    first_evidence = acquire_authorized_target_rows_v1(
        preregistration,
        proposal,
        context,
        first_authorization,
        kernel,
        initial_catalogues,
    )
    first_evidence_verification = verify_target_relational_evidence_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        first_audit,
        first_authorization,
        first_evidence,
        kernel,
        initial_catalogues,
    )
    intermediate_model = build_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        (first_evidence,),
        (first_evidence_verification,),
    )
    second_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        calibration,
        initial_catalogues,
    )
    second_authorization = authorize_failed_relational_support_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        second_audit,
        2,
    )
    successor_catalogues = successor_catalogues_from_evidence_v1(first_evidence)
    second_evidence = acquire_authorized_target_rows_v1(
        preregistration,
        proposal,
        context,
        second_authorization,
        kernel,
        successor_catalogues,
    )
    second_evidence_verification = verify_target_relational_evidence_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        second_audit,
        second_authorization,
        second_evidence,
        kernel,
        successor_catalogues,
    )
    final_model = build_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        (first_evidence, second_evidence),
        (first_evidence_verification, second_evidence_verification),
    )
    final_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        final_model,
        calibration,
        initial_catalogues,
    )
    occurrences = tuple(
        item
        for item in preregistration.occurrences
        if item.context_id == context.context_id
    )
    occurrence_audits: list[RelationalModelOnlyAuditV1] = []
    direct_controls: list[ColdDirectGroundControlV1] = []
    by_board = {item[0].board: item for item in initial_catalogues}
    for occurrence in occurrences:
        occurrence_audits.append(
            audit_relational_partial_model_v1(
                preregistration,
                proposal,
                context,
                final_model,
                calibration,
                (by_board[occurrence.initial_board],),
                occurrence=occurrence,
            )
        )
        direct_controls.append(_cold_direct_ground_control(occurrence, context))
    return RelationalTargetContextResultV1(
        context,
        initial_model,
        first_audit,
        first_authorization,
        first_evidence,
        first_evidence_verification,
        intermediate_model,
        second_audit,
        second_authorization,
        second_evidence,
        second_evidence_verification,
        final_model,
        final_audit,
        tuple(occurrence_audits),
        tuple(direct_controls),
        24,
        (0, 0),
    )


@dataclass(frozen=True, slots=True)
class WrongRelationalProposalControlV1:
    context_id: str
    wrong_decisions: tuple[ProposedAbstractDecisionV1, ...]
    first_audit_id: str
    second_audit_id: str
    evidence_verification_ids: tuple[str, ...]
    final_audit: RelationalModelOnlyAuditV1
    acquired_ground_row_count: int
    generative_sample_count: int
    false_certificate_count: int
    fallback_required: bool

    def __post_init__(self) -> None:
        _cid(self.context_id, "wrong-control context")
        _cid(self.first_audit_id, "wrong-control first audit")
        _cid(self.second_audit_id, "wrong-control second audit")
        if (
            type(self.evidence_verification_ids) is not tuple
            or len(self.evidence_verification_ids) != 2
        ):
            raise RelationalSupportInvariantViolation(
                "wrong-control evidence verification chain is incomplete"
            )
        for item in self.evidence_verification_ids:
            _cid(item, "wrong-control evidence verification")
        _exact_tuple(
            self.wrong_decisions,
            ProposedAbstractDecisionV1,
            "wrong decisions",
        )
        if (
            type(self.final_audit) is not RelationalModelOnlyAuditV1
            or self.final_audit.outcome is not TargetAuditOutcome.FAILED_RISK
            or self.acquired_ground_row_count != 16
            or self.generative_sample_count
            != 16 * SAMPLE_COUNT_PER_GROUND_ROW
            or self.false_certificate_count != 0
            or self.fallback_required is not True
        ):
            raise RelationalSupportInvariantViolation(
                "wrong-proposal negative control changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.wrong_relational_proposal_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "wrong_decisions": [
                item.to_document() for item in self.wrong_decisions
            ],
            "first_audit_id": self.first_audit_id,
            "second_audit_id": self.second_audit_id,
            "evidence_verification_ids": list(
                self.evidence_verification_ids
            ),
            "final_audit_id": self.final_audit.audit_id,
            "final_failure_upper": _fdoc(self.final_audit.failure_upper),
            "acquired_ground_row_count": self.acquired_ground_row_count,
            "generative_sample_count": self.generative_sample_count,
            "false_certificate_count": self.false_certificate_count,
            "fallback_required": self.fallback_required,
        }

    @property
    def wrong_control_id(self) -> str:
        return _content_id("wrong", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "wrong_control_id": self.wrong_control_id}


def _wrong_decision_override(
    proposal: RelationalCoordinateSupportProposalV1,
    initial_catalogues: tuple[
        tuple[RawRelationalStateV1, tuple[RawRelationalActionV1, ...]],
        ...,
    ],
) -> dict[tuple[int, tuple[str, Any]], tuple[str, Any]]:
    decisions = _decision_lookup(proposal)
    state, catalogue = initial_catalogues[0]
    state_value = _normalized_program_value(
        proposal.state_program,
        _eval_program(
            proposal.state_program,
            _EvaluationCovariate(state, None, catalogue),
        ),
    )
    available = tuple(
        sorted(
            {
                _normalized_program_value(
                    proposal.action_program,
                    _eval_program(
                        proposal.action_program,
                        _EvaluationCovariate(state, action, catalogue),
                    ),
                )
                for action in catalogue
            },
            key=repr,
        )
    )
    key = (HORIZON, state_value)
    alternatives = tuple(item for item in available if item != decisions[key])
    if len(alternatives) != 1:
        raise RelationalSupportInvariantViolation(
            "wrong-proposal control requires one root alternative"
        )
    decisions[key] = alternatives[0]
    return decisions


def _run_wrong_proposal_control(
    preregistration: RelationalFamilyPreregistrationV1,
    proposal: RelationalCoordinateSupportProposalV1,
    context: RelationalStructuralContextV1,
    calibration: RelationalHoeffdingCalibrationV1,
) -> WrongRelationalProposalControlV1:
    kernel = _kernel_for_context(context)
    initial_catalogues = _initial_target_catalogues(context, kernel)
    override = _wrong_decision_override(proposal, initial_catalogues)
    initial_model = initial_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
    )
    first_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        calibration,
        initial_catalogues,
        decision_override=override,
    )
    first_authorization = authorize_failed_relational_support_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        first_audit,
        1,
    )
    first_evidence = acquire_authorized_target_rows_v1(
        preregistration,
        proposal,
        context,
        first_authorization,
        kernel,
        initial_catalogues,
    )
    first_evidence_verification = verify_target_relational_evidence_v1(
        preregistration,
        proposal,
        context,
        initial_model,
        first_audit,
        first_authorization,
        first_evidence,
        kernel,
        initial_catalogues,
    )
    intermediate_model = build_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        (first_evidence,),
        (first_evidence_verification,),
    )
    second_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        calibration,
        initial_catalogues,
        decision_override=override,
    )
    second_authorization = authorize_failed_relational_support_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        second_audit,
        2,
    )
    second_evidence = acquire_authorized_target_rows_v1(
        preregistration,
        proposal,
        context,
        second_authorization,
        kernel,
        successor_catalogues_from_evidence_v1(first_evidence),
    )
    second_catalogues = successor_catalogues_from_evidence_v1(first_evidence)
    second_evidence_verification = verify_target_relational_evidence_v1(
        preregistration,
        proposal,
        context,
        intermediate_model,
        second_audit,
        second_authorization,
        second_evidence,
        kernel,
        second_catalogues,
    )
    final_model = build_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        (first_evidence, second_evidence),
        (first_evidence_verification, second_evidence_verification),
    )
    final_audit = audit_relational_partial_model_v1(
        preregistration,
        proposal,
        context,
        final_model,
        calibration,
        initial_catalogues,
        decision_override=override,
    )
    wrong_decisions = tuple(
        ProposedAbstractDecisionV1(remaining, state_value, action_value)
        for (remaining, state_value), action_value in sorted(override.items(), key=repr)
    )
    return WrongRelationalProposalControlV1(
        context.context_id,
        wrong_decisions,
        first_audit.audit_id,
        second_audit.audit_id,
        (
            first_evidence_verification.verification_id,
            second_evidence_verification.verification_id,
        ),
        final_audit,
        first_evidence.ground_transition_row_count
        + second_evidence.ground_transition_row_count,
        first_evidence.generative_sample_count
        + second_evidence.generative_sample_count,
        0,
        True,
    )


@dataclass(frozen=True, slots=True)
class RelationalHoeffdingCalibrationV1:
    sample_count_per_ground_row: int
    radius: Fraction
    coordinate_obligation_count: int
    exponent: Fraction
    taylor_degree: int
    taylor_lower: Fraction
    exponential_denominator_lower: int
    per_coordinate_tail_upper: Fraction
    family_tail_upper: Fraction
    family_confidence_lower: Fraction
    theorem_id: str = (
        "two_sided_hoeffding_exact_taylor_lower_finite_union_v1"
    )

    def __post_init__(self) -> None:
        expected_exponent = (
            2 * SAMPLE_COUNT_PER_GROUND_ROW * HOEFFDING_RADIUS**2
        )
        expected_taylor = sum(
            (
                expected_exponent**index / math.factorial(index)
                for index in range(14)
            ),
            Fraction(0),
        )
        if (
            self.sample_count_per_ground_row
            != SAMPLE_COUNT_PER_GROUND_ROW
            or self.radius != HOEFFDING_RADIUS
            or self.coordinate_obligation_count != 176
            or self.exponent != expected_exponent
            or self.exponent != Fraction(2048, 225)
            or self.taylor_degree != 13
            or self.taylor_lower != expected_taylor
            or self.taylor_lower <= self.exponential_denominator_lower
            or self.exponential_denominator_lower != 8000
            or self.per_coordinate_tail_upper
            != Fraction(2, self.exponential_denominator_lower)
            or self.per_coordinate_tail_upper
            != PER_COORDINATE_TAIL_UPPER
            or self.family_tail_upper
            != self.coordinate_obligation_count
            * self.per_coordinate_tail_upper
            or self.family_tail_upper != Fraction(11, 250)
            or self.family_confidence_lower
            != 1 - self.family_tail_upper
            or self.family_confidence_lower != Fraction(239, 250)
            or self.theorem_id
            != "two_sided_hoeffding_exact_taylor_lower_finite_union_v1"
        ):
            raise RelationalSupportInvariantViolation(
                "relational Hoeffding calibration is not the frozen exact proof"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_hoeffding_calibration.v1",
            "schema_version": SCHEMA_VERSION,
            "sample_count_per_ground_row": self.sample_count_per_ground_row,
            "radius": _fdoc(self.radius),
            "coordinate_obligation_count": self.coordinate_obligation_count,
            "exponent": _fdoc(self.exponent),
            "taylor_degree": self.taylor_degree,
            "taylor_lower": _fdoc(self.taylor_lower),
            "exponential_denominator_lower": (
                self.exponential_denominator_lower
            ),
            "per_coordinate_tail_upper": _fdoc(
                self.per_coordinate_tail_upper
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(
                self.family_confidence_lower
            ),
            "theorem_id": self.theorem_id,
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "calibration_id": self.calibration_id}


def relational_hoeffding_calibration_v1() -> RelationalHoeffdingCalibrationV1:
    exponent = 2 * SAMPLE_COUNT_PER_GROUND_ROW * HOEFFDING_RADIUS**2
    taylor = sum(
        (
            exponent**index / math.factorial(index)
            for index in range(14)
        ),
        Fraction(0),
    )
    obligations = 176
    family_tail = obligations * PER_COORDINATE_TAIL_UPPER
    return RelationalHoeffdingCalibrationV1(
        SAMPLE_COUNT_PER_GROUND_ROW,
        HOEFFDING_RADIUS,
        obligations,
        exponent,
        13,
        taylor,
        8000,
        PER_COORDINATE_TAIL_UPPER,
        family_tail,
        1 - family_tail,
    )


@dataclass(frozen=True, slots=True)
class RelationalSupportCampaignV1:
    preregistration: RelationalFamilyPreregistrationV1
    source_log: SourceRelationalObservationLogV1
    proposal: RelationalCoordinateSupportProposalV1
    target_results: tuple[RelationalTargetContextResultV1, ...]
    wrong_control: WrongRelationalProposalControlV1
    calibration: RelationalHoeffdingCalibrationV1
    source_ground_row_count: int
    target_ground_row_count: int
    target_generative_sample_count: int
    wrong_ground_row_count: int
    wrong_generative_sample_count: int
    cold_direct_exact_ground_row_count: int
    statistical_coordinate_obligations: int
    family_tail_upper: Fraction
    family_confidence_lower: Fraction
    status: str = SUCCESS_STATUS
    automatic_coordinate_selection_claimed: bool = True
    automatic_anonymous_support_proposal_claimed: bool = True
    known_group_prior_used: bool = False
    named_frontier_used: bool = False
    target_only_certificate_claimed: bool = True
    registered_symbolic_outcome_support_used: bool = True
    unknown_outcome_support_claimed: bool = False
    post_context_build_query_reuse_claimed: bool = True
    sequential_occurrence_acquisition_claimed: bool = False
    cross_structural_rapm_reuse_claimed: bool = False
    primitive_invention_claimed: bool = False
    broad_generalization_claimed: bool = False
    sample_efficiency_claimed: bool = False
    same_implementation_semantic_replay_claimed: bool = True
    independent_algorithm_verification_claimed: bool = False
    official_execution_allowed: bool = False
    official_scalar_cost: None = None
    official_N_break_even: None = None

    def __post_init__(self) -> None:
        if (
            type(self.preregistration) is not RelationalFamilyPreregistrationV1
            or type(self.source_log) is not SourceRelationalObservationLogV1
            or type(self.proposal) is not RelationalCoordinateSupportProposalV1
            or type(self.wrong_control) is not WrongRelationalProposalControlV1
            or type(self.calibration) is not RelationalHoeffdingCalibrationV1
        ):
            raise RelationalSupportInvariantViolation(
                "campaign rejects substituted authority objects"
            )
        _exact_tuple(
            self.target_results,
            RelationalTargetContextResultV1,
            "campaign target results",
        )
        expected_target_rows = 3 * 24
        expected_wrong_rows = 16
        expected_direct_rows = 6 * 18
        expected_obligations = 2 * (expected_target_rows + expected_wrong_rows)
        if (
            self.source_log.contexts != self.preregistration.source_contexts
            or self.proposal.source_log_id != self.source_log.log_id
            or len(self.target_results) != 3
            or tuple(item.context for item in self.target_results)
            != self.preregistration.target_contexts
            or self.source_ground_row_count != 144
            or self.target_ground_row_count != expected_target_rows
            or self.target_generative_sample_count
            != expected_target_rows * SAMPLE_COUNT_PER_GROUND_ROW
            or self.wrong_ground_row_count != expected_wrong_rows
            or self.wrong_generative_sample_count
            != expected_wrong_rows * SAMPLE_COUNT_PER_GROUND_ROW
            or self.cold_direct_exact_ground_row_count != expected_direct_rows
            or self.statistical_coordinate_obligations != expected_obligations
            or self.calibration.coordinate_obligation_count
            != expected_obligations
            or self.family_tail_upper
            != self.calibration.family_tail_upper
            or self.family_confidence_lower != 1 - self.family_tail_upper
            or self.family_confidence_lower
            != self.calibration.family_confidence_lower
            or self.status != SUCCESS_STATUS
            or self.automatic_coordinate_selection_claimed is not True
            or self.automatic_anonymous_support_proposal_claimed is not True
            or self.known_group_prior_used is not False
            or self.named_frontier_used is not False
            or self.target_only_certificate_claimed is not True
            or self.registered_symbolic_outcome_support_used is not True
            or self.unknown_outcome_support_claimed is not False
            or self.post_context_build_query_reuse_claimed is not True
            or self.sequential_occurrence_acquisition_claimed is not False
            or self.cross_structural_rapm_reuse_claimed is not False
            or self.primitive_invention_claimed is not False
            or self.broad_generalization_claimed is not False
            or self.sample_efficiency_claimed is not False
            or self.same_implementation_semantic_replay_claimed is not True
            or self.independent_algorithm_verification_claimed is not False
            or self.official_execution_allowed is not False
            or self.official_scalar_cost is not None
            or self.official_N_break_even is not None
        ):
            raise RelationalSupportInvariantViolation(
                "campaign totals, result ordering, or claim boundary changed"
            )
        if any(
            item.final_audit.outcome is not TargetAuditOutcome.CERTIFIED
            or item.context_build_ground_rows != 24
            or item.occurrence_new_ground_rows != (0, 0)
            for item in self.target_results
        ):
            raise RelationalSupportInvariantViolation(
                "campaign target certificate/reuse invariant failed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_support_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "status": self.status,
            "preregistration_id": self.preregistration.preregistration_id,
            "source_log_id": self.source_log.log_id,
            "proposal_id": self.proposal.proposal_id,
            "target_result_ids": [
                item.context_result_id for item in self.target_results
            ],
            "wrong_control_id": self.wrong_control.wrong_control_id,
            "calibration_id": self.calibration.calibration_id,
            "source_ground_row_count": self.source_ground_row_count,
            "target_ground_row_count": self.target_ground_row_count,
            "target_generative_sample_count": (
                self.target_generative_sample_count
            ),
            "wrong_ground_row_count": self.wrong_ground_row_count,
            "wrong_generative_sample_count": (
                self.wrong_generative_sample_count
            ),
            "cold_direct_exact_ground_row_count": (
                self.cold_direct_exact_ground_row_count
            ),
            "statistical_coordinate_obligations": (
                self.statistical_coordinate_obligations
            ),
            "per_coordinate_tail_upper": _fdoc(PER_COORDINATE_TAIL_UPPER),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(self.family_confidence_lower),
            "automatic_coordinate_selection_claimed": (
                self.automatic_coordinate_selection_claimed
            ),
            "automatic_anonymous_support_proposal_claimed": (
                self.automatic_anonymous_support_proposal_claimed
            ),
            "known_group_prior_used": self.known_group_prior_used,
            "named_frontier_used": self.named_frontier_used,
            "target_only_certificate_claimed": (
                self.target_only_certificate_claimed
            ),
            "registered_symbolic_outcome_support_used": (
                self.registered_symbolic_outcome_support_used
            ),
            "unknown_outcome_support_claimed": (
                self.unknown_outcome_support_claimed
            ),
            "post_context_build_query_reuse_claimed": (
                self.post_context_build_query_reuse_claimed
            ),
            "sequential_occurrence_acquisition_claimed": (
                self.sequential_occurrence_acquisition_claimed
            ),
            "cross_structural_rapm_reuse_claimed": (
                self.cross_structural_rapm_reuse_claimed
            ),
            "primitive_invention_claimed": self.primitive_invention_claimed,
            "broad_generalization_claimed": self.broad_generalization_claimed,
            "sample_efficiency_claimed": self.sample_efficiency_claimed,
            "same_implementation_semantic_replay_claimed": (
                self.same_implementation_semantic_replay_claimed
            ),
            "independent_algorithm_verification_claimed": (
                self.independent_algorithm_verification_claimed
            ),
            "official_execution_allowed": self.official_execution_allowed,
            "official_scalar_cost": self.official_scalar_cost,
            "official_N_break_even": self.official_N_break_even,
            "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
            "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
            "SAMPLE_EFFICIENCY_GATE": "NOT_RUN",
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "campaign_id": self.campaign_id}


def _run_relational_support_campaign_uncached_v1() -> RelationalSupportCampaignV1:
    preregistration = preregister_relational_support_family_v1()
    source_log = acquire_source_relational_observations_v1(
        preregistration.source_contexts
    )
    proposal = synthesize_relational_coordinate_support_v1(source_log)
    calibration = relational_hoeffding_calibration_v1()
    target_results = tuple(
        _run_target_context(
            preregistration,
            proposal,
            context,
            calibration,
        )
        for context in preregistration.target_contexts
    )
    wrong_control = _run_wrong_proposal_control(
        preregistration,
        proposal,
        preregistration.target_contexts[0],
        calibration,
    )
    target_rows = sum(item.target_ground_row_count for item in target_results)
    target_samples = sum(item.target_sample_count for item in target_results)
    direct_rows = sum(
        item.reachable_state_action_row_count
        for result in target_results
        for item in result.direct_controls
    )
    obligations = 2 * (
        target_rows + wrong_control.acquired_ground_row_count
    )
    return RelationalSupportCampaignV1(
        preregistration,
        source_log,
        proposal,
        target_results,
        wrong_control,
        calibration,
        len(source_log.rows),
        target_rows,
        target_samples,
        wrong_control.acquired_ground_row_count,
        wrong_control.generative_sample_count,
        direct_rows,
        obligations,
        obligations * PER_COORDINATE_TAIL_UPPER,
        1 - obligations * PER_COORDINATE_TAIL_UPPER,
    )


@functools.lru_cache(maxsize=1)
def _cached_relational_support_campaign_v1() -> RelationalSupportCampaignV1:
    return _run_relational_support_campaign_uncached_v1()


def run_relational_support_campaign_v1(
    *,
    fresh: bool = False,
) -> RelationalSupportCampaignV1:
    _validate_implementation_authority_v1()
    return (
        _run_relational_support_campaign_uncached_v1()
        if fresh
        else _cached_relational_support_campaign_v1()
    )


@dataclass(frozen=True, slots=True)
class RelationalSupportVerificationV1:
    campaign_id: str
    replayed_source_row_count: int
    replayed_target_ground_row_count: int
    replayed_target_sample_count: int
    replayed_direct_ground_row_count: int
    exact_comparator_count: int
    proposal_byte_identical: bool
    target_results_byte_identical: bool
    wrong_control_byte_identical: bool
    raw_draws_replayed: bool
    claim_boundary_valid: bool
    independent_algorithm_verification: bool = False
    verifier_kind: str = "same_implementation_full_semantic_replay_v1"
    status: str = "VERIFIED_RELATIONAL_SUPPORT_CAMPAIGN"

    def __post_init__(self) -> None:
        _cid(self.campaign_id, "verification campaign")
        if (
            self.replayed_source_row_count != 144
            or self.replayed_target_ground_row_count != 88
            or self.replayed_target_sample_count
            != 88 * SAMPLE_COUNT_PER_GROUND_ROW
            or self.replayed_direct_ground_row_count != 108
            or self.exact_comparator_count != 6
            or self.proposal_byte_identical is not True
            or self.target_results_byte_identical is not True
            or self.wrong_control_byte_identical is not True
            or self.raw_draws_replayed is not True
            or self.claim_boundary_valid is not True
            or self.independent_algorithm_verification is not False
            or self.verifier_kind
            != "same_implementation_full_semantic_replay_v1"
            or self.status != "VERIFIED_RELATIONAL_SUPPORT_CAMPAIGN"
        ):
            raise RelationalSupportInvariantViolation(
                "relational support verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.relational_support_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "replayed_source_row_count": self.replayed_source_row_count,
            "replayed_target_ground_row_count": (
                self.replayed_target_ground_row_count
            ),
            "replayed_target_sample_count": self.replayed_target_sample_count,
            "replayed_direct_ground_row_count": (
                self.replayed_direct_ground_row_count
            ),
            "exact_comparator_count": self.exact_comparator_count,
            "proposal_byte_identical": self.proposal_byte_identical,
            "target_results_byte_identical": self.target_results_byte_identical,
            "wrong_control_byte_identical": self.wrong_control_byte_identical,
            "raw_draws_replayed": self.raw_draws_replayed,
            "claim_boundary_valid": self.claim_boundary_valid,
            "independent_algorithm_verification": (
                self.independent_algorithm_verification
            ),
            "verifier_kind": self.verifier_kind,
            "status": self.status,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_relational_support_campaign_v1(
    claimed: RelationalSupportCampaignV1,
) -> RelationalSupportVerificationV1:
    _validate_implementation_authority_v1()
    if type(claimed) is not RelationalSupportCampaignV1:
        raise RelationalSupportInvariantViolation(
            "verifier rejects substituted campaigns"
        )
    expected = _run_relational_support_campaign_uncached_v1()
    _runtime_shape(claimed, expected, "relational campaign")
    if claimed.to_document() != expected.to_document():
        raise RelationalSupportInvariantViolation(
            "relational campaign differs from independent replay"
        )
    return RelationalSupportVerificationV1(
        claimed.campaign_id,
        len(expected.source_log.rows),
        expected.target_ground_row_count + expected.wrong_ground_row_count,
        expected.target_generative_sample_count
        + expected.wrong_generative_sample_count,
        expected.cold_direct_exact_ground_row_count,
        sum(len(item.direct_controls) for item in expected.target_results),
        claimed.proposal.to_document() == expected.proposal.to_document(),
        tuple(item.to_document() for item in claimed.target_results)
        == tuple(item.to_document() for item in expected.target_results),
        claimed.wrong_control.to_document()
        == expected.wrong_control.to_document(),
        True,
        (
            claimed.known_group_prior_used is False
            and claimed.named_frontier_used is False
            and claimed.cross_structural_rapm_reuse_claimed is False
            and claimed.primitive_invention_claimed is False
            and claimed.broad_generalization_claimed is False
            and claimed.sample_efficiency_claimed is False
            and claimed.official_execution_allowed is False
            and claimed.same_implementation_semantic_replay_claimed is True
            and claimed.independent_algorithm_verification_claimed is False
        ),
    )


def _implementation_authority_items_v1() -> tuple[Any, ...]:
    excluded = {
        "_implementation_authority_items_v1",
        "_observed_implementation_sha256_v1",
        "_observed_kernel_implementation_sha256_v1",
        "_validate_implementation_authority_v1",
    }
    return tuple(
        value
        for name, value in sorted(globals().items())
        if name not in excluded
        and getattr(value, "__module__", None) == __name__
        and (inspect.isfunction(value) or inspect.isclass(value))
    )


def _observed_implementation_sha256_v1() -> str:
    source = "\n\n".join(
        inspect.getsource(item)
        for item in _implementation_authority_items_v1()
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _observed_kernel_implementation_sha256_v1() -> str:
    source = "\n\n".join(
        inspect.getsource(item)
        for item in (
            G2048State,
            G2048Action,
            G2048Kernel,
            RankRelativeAcquisitionKernelV1,
        )
    )
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def _validate_implementation_authority_v1() -> None:
    if (
        _observed_implementation_sha256_v1() != IMPLEMENTATION_SHA256
        or _observed_kernel_implementation_sha256_v1()
        != KERNEL_IMPLEMENTATION_SHA256
    ):
        raise RelationalSupportInvariantViolation(
            "V0-064 implementation or kernel differs from frozen authority"
        )


__all__ = [
    "CONTRACT_VERSION",
    "ContextSplit",
    "HeldOutRelationalOccurrenceV1",
    "IMPLEMENTATION_SHA256",
    "KERNEL_IMPLEMENTATION_SHA256",
    "PROFILE_KEY",
    "RelationalCandidateTraceV1",
    "RelationalCoordinateProgramV1",
    "RelationalCoordinateSupportProposalV1",
    "RelationalFamilyPreregistrationV1",
    "RelationalModelOnlyAuditV1",
    "RelationalHoeffdingCalibrationV1",
    "RelationalPartialStatisticalModelV1",
    "RelationalProgramRegistryV1",
    "RelationalStructuralContextV1",
    "RelationalSupportCampaignV1",
    "RelationalSupportInvariantViolation",
    "RelationalSupportVerificationV1",
    "SUCCESS_STATUS",
    "TargetAuditOutcome",
    "TargetEvidenceVerificationV1",
    "acquire_source_relational_observations_v1",
    "audit_relational_partial_model_v1",
    "generate_relational_program_closure_v1",
    "preregister_relational_support_family_v1",
    "registered_relational_contexts_v1",
    "relational_hoeffding_calibration_v1",
    "run_relational_support_campaign_v1",
    "select_relational_coordinate_candidate_v1",
    "synthesize_relational_coordinate_support_v1",
    "verify_target_relational_evidence_v1",
    "verify_relational_support_campaign_v1",
]
