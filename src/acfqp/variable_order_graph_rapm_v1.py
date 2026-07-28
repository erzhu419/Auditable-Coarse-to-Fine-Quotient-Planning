"""Sparse variable-order graph RAPM campaign for V0-066.

This module is deliberately a new authority.  It does not modify or extend
the frozen V0-065 four-vertex foundation.  The source side is represented by
the portable relational skeleton in :mod:`portable_relational_skeleton_v1`;
the target side contains only five- and six-vertex graph processes.

The sparse construction path never constructs a complete target H2 closure.
It materializes both root rows, authorizes a semantic action from those rows,
and then materializes only that action's proof cone.  A failed abstract proof
may invoke a separately charged exact fallback over the matched root query.
No operational path constructs a family-wide or all-motif closure; matched
direct controls remain in the evaluation lane.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, replace
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import combinations, permutations
import math
import functools
from typing import Any, Iterable, Mapping

from acfqp.cross_graph_relational_support_v1 import (
    CrossGraphStructuralContextV1,
    acquire_cross_graph_source_observations_v1,
    registered_cross_graph_contexts_v1,
)
from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.portable_relational_skeleton_v1 import (
    AnonymousRelationalObservationLogV1,
    FailedRelationalProofRefV1,
    PortableRelationalProgramV1,
    PortableRelationalRoleSchemaV1,
    PortableRelationalSkeletonV1,
    PortableRelationalSynthesisMetricsV1,
    RelationalActionSlotV1,
    RelationalObservedRowV1,
    RelationalOutcomeIRV1,
    RelationalProgramContext,
    RelationalProgramType,
    RelationalStateIRV1,
    TargetRelationalProgramGenerationV1,
    evaluate_portable_action_program_v1,
    evaluate_portable_state_program_v1,
    generate_target_relational_programs_v1,
    portable_relational_synthesis_metrics_v1,
    synthesize_portable_relational_skeleton_v1,
    syntactic_portable_program_closure_v1,
    verify_portable_relational_skeleton_v1,
)
from acfqp.relational_graph_core_v1 import (
    GraphActionViewV1,
    GraphStateViewV1,
    GraphTopologyV1,
)


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.30.0"
PROFILE_KEY = "sparse_variable_order_graph_rapm_v0"
REGISTERED_PRNG_SEMANTICS_ID = "splitmix64_counter_stream_v1"
STATISTICAL_CLAIM_SCOPE = (
    "CONDITIONAL_ON_REGISTERED_PRNG_UINT64_IID_SIMULATOR_ASSUMPTION"
)

HORIZON = 2
RANK_CAP = 6
LOW_RANK = 1
LOW_RANK_PROBABILITY = Fraction(99, 100)
POSITIVE_RISK_TOLERANCE = Fraction(1, 20)
NO_COVER_RISK_TOLERANCE = Fraction(1, 5)
REWARD_NORMALIZER = Fraction(HORIZON)

SAMPLE_COUNT_PER_ROW = 131_072
HOEFFDING_RADIUS = Fraction(1, 140)
PER_OBLIGATION_TAIL_UPPER = Fraction(1, 250_000)
SOURCE_VERTEX_COUNTS = (4,)
TARGET_VERTEX_COUNTS = (5, 6)


class VariableOrderGraphInvariantViolation(ValueError):
    """A registered graph, evidence, model, proof, or control is invalid."""


DOMAIN_TAGS = {
    "context": "acfqp:variable-order-graph-context:v1",
    "sampling_context": "acfqp:variable-order-graph-sampling-context:v1",
    "family": "acfqp:variable-order-graph-family:v1",
    "state": "acfqp:variable-order-graph-state:v1",
    "catalogue": "acfqp:variable-order-graph-catalogue:v1",
    "authorization": "acfqp:variable-order-graph-root-cone-authorization:v1",
    "atom": "acfqp:variable-order-graph-atom:v1",
    "row": "acfqp:variable-order-graph-packed-row:v1",
    "evidence": "acfqp:variable-order-graph-evidence:v1",
    "verification": "acfqp:variable-order-graph-evidence-verification:v1",
    "profile": "acfqp:variable-order-graph-coordinate-profile:v1",
    "model": "acfqp:variable-order-graph-partial-rapm:v1",
    "audit": "acfqp:variable-order-graph-audit:v1",
    "policy": "acfqp:variable-order-graph-abstract-policy:v1",
    "generation": "acfqp:variable-order-graph-program-generation:v1",
    "coverage": "acfqp:variable-order-graph-sparse-coverage:v1",
    "access": "acfqp:variable-order-graph-access-log:v1",
    "cold": "acfqp:variable-order-graph-cold-control:v1",
    "fallback": "acfqp:variable-order-graph-exact-fallback-proof:v1",
    "evaluation": "acfqp:variable-order-graph-matched-evaluation:v1",
    "result": "acfqp:variable-order-graph-result:v1",
    "calibration": "acfqp:variable-order-graph-calibration:v1",
    "campaign": "acfqp:variable-order-graph-campaign:v1",
    "campaign_verification": (
        "acfqp:variable-order-graph-campaign-verification:v1"
    ),
    "query": "acfqp:variable-order-graph-query:v1",
    "occurrence": "acfqp:variable-order-graph-query-occurrence:v1",
    "permutation": "acfqp:variable-order-graph-permutation-control:v1",
    "no_transfer": "acfqp:variable-order-graph-no-transfer-control:v1",
}


def _content_id(role: str, payload: Mapping[str, Any]) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        body = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise VariableOrderGraphInvariantViolation(str(error)) from error
    return hashlib.sha256(tag + b"\x00" + body).hexdigest()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise VariableOrderGraphInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {"numerator": exact.numerator, "denominator": exact.denominator}


def _graph_edges(rows: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({tuple(sorted(item)) for item in rows}))


W5_EDGES = _graph_edges(
    (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 0),
        (4, 1),
        (4, 2),
        (4, 3),
    )
)
K6_EDGES = tuple(combinations(range(6), 2))
K6_MINUS_EDGE_EDGES = tuple(
    edge for edge in combinations(range(6), 2) if edge != (4, 5)
)


class GraphTargetRole(str, Enum):
    POSITIVE = "POSITIVE"
    NO_SOUND_COVER = "NO_SOUND_COVER"


@dataclass(frozen=True, slots=True)
class VariableOrderGraphContextV1:
    context_key: str
    topology: GraphTopologyV1
    root_board: tuple[int, ...]
    risk_tolerance: Fraction

    def __post_init__(self) -> None:
        registered = {
            "variable_target_w5_v0": (
                GraphTopologyV1(5, W5_EDGES),
                (1, 1, 2, 0, 0),
                POSITIVE_RISK_TOLERANCE,
            ),
            "variable_target_k6_v0": (
                GraphTopologyV1(6, K6_EDGES),
                (1, 1, 2, 0, 0, 0),
                POSITIVE_RISK_TOLERANCE,
            ),
            "variable_negative_k6_minus_edge_v0": (
                GraphTopologyV1(6, K6_MINUS_EDGE_EDGES),
                (0, 2, 1, 1, 0, 0),
                NO_COVER_RISK_TOLERANCE,
            ),
        }
        if (
            type(self.context_key) is not str
            or type(self.topology) is not GraphTopologyV1
            or type(self.root_board) is not tuple
            or type(self.risk_tolerance) is not Fraction
            or registered.get(self.context_key)
            != (
                self.topology,
                self.root_board,
                self.risk_tolerance,
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable-order graph context is not registered"
            )

    @property
    def vertex_count(self) -> int:
        return self.topology.vertex_count

    @property
    def sampling_context_id(self) -> str:
        return _content_id(
            "sampling_context",
            {
                "schema": "acfqp.variable_order_graph_sampling_context.v1",
                "schema_version": SCHEMA_VERSION,
                "topology": self.topology.to_document(),
                "root_board": list(self.root_board),
                "horizon": HORIZON,
                "rank_cap": RANK_CAP,
                "spawn_support": [LOW_RANK, LOW_RANK + 1],
                "sampler_semantics_id": REGISTERED_PRNG_SEMANTICS_ID,
            },
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_key": self.context_key,
            "topology": self.topology.to_document(),
            "root_board": list(self.root_board),
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "horizon": HORIZON,
            "rank_cap": RANK_CAP,
            "spawn_support": [LOW_RANK, LOW_RANK + 1],
            "sampler_semantics_id": REGISTERED_PRNG_SEMANTICS_ID,
            "probability_access": "ACQUISITION_OR_EVALUATION_AUTHORITY_ONLY",
            "sampling_context_id": self.sampling_context_id,
        }

    @property
    def context_id(self) -> str:
        return _content_id("context", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_variable_order_contexts_v1(
) -> tuple[VariableOrderGraphContextV1, ...]:
    return (
        VariableOrderGraphContextV1(
            "variable_target_w5_v0",
            GraphTopologyV1(5, W5_EDGES),
            (1, 1, 2, 0, 0),
            POSITIVE_RISK_TOLERANCE,
        ),
        VariableOrderGraphContextV1(
            "variable_target_k6_v0",
            GraphTopologyV1(6, K6_EDGES),
            (1, 1, 2, 0, 0, 0),
            POSITIVE_RISK_TOLERANCE,
        ),
        VariableOrderGraphContextV1(
            "variable_negative_k6_minus_edge_v0",
            GraphTopologyV1(6, K6_MINUS_EDGE_EDGES),
            (0, 2, 1, 1, 0, 0),
            NO_COVER_RISK_TOLERANCE,
        ),
    )


def registered_graph_target_role_v1(
    context: VariableOrderGraphContextV1,
) -> GraphTargetRole:
    if (
        type(context) is not VariableOrderGraphContextV1
        or context not in registered_variable_order_contexts_v1()
    ):
        raise VariableOrderGraphInvariantViolation(
            "evaluation role requires a registered context"
        )
    return (
        GraphTargetRole.NO_SOUND_COVER
        if context.context_key == "variable_negative_k6_minus_edge_v0"
        else GraphTargetRole.POSITIVE
    )


@dataclass(frozen=True, slots=True)
class VariableOrderGraphFamilyV1:
    contexts: tuple[VariableOrderGraphContextV1, ...]
    source_vertex_counts: tuple[int, ...] = SOURCE_VERTEX_COUNTS
    target_vertex_counts: tuple[int, ...] = TARGET_VERTEX_COUNTS
    source_target_counts_disjoint: bool = True

    def __post_init__(self) -> None:
        if (
            self.contexts != registered_variable_order_contexts_v1()
            or self.source_vertex_counts != SOURCE_VERTEX_COUNTS
            or self.target_vertex_counts != TARGET_VERTEX_COUNTS
            or set(self.source_vertex_counts) & set(self.target_vertex_counts)
            or {
                item.vertex_count for item in self.contexts
            }
            != set(self.target_vertex_counts)
            or self.source_target_counts_disjoint is not True
        ):
            raise VariableOrderGraphInvariantViolation(
                "source/target vertex-count split is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_family.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "contexts": [item.to_document() for item in self.contexts],
            "evaluation_roles": [
                {
                    "context_id": item.context_id,
                    "role": registered_graph_target_role_v1(item).value,
                }
                for item in self.contexts
            ],
            "source_vertex_counts": list(self.source_vertex_counts),
            "target_vertex_counts": list(self.target_vertex_counts),
            "source_target_counts_disjoint": True,
        }

    @property
    def family_id(self) -> str:
        return _content_id("family", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "family_id": self.family_id}


def registered_variable_order_family_v1() -> VariableOrderGraphFamilyV1:
    return VariableOrderGraphFamilyV1(registered_variable_order_contexts_v1())


@dataclass(frozen=True, slots=True)
class VariableGraphStateV1:
    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) not in TARGET_VERTEX_COUNTS
            or any(
                type(rank) is not int or not 0 <= rank <= RANK_CAP
                for rank in self.ranks
            )
            or type(self.failure) is not bool
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable-order graph state is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_state.v1",
            "schema_version": SCHEMA_VERSION,
            "ranks": list(self.ranks),
            "failure": self.failure,
        }

    @property
    def state_id(self) -> str:
        return _content_id("state", self._payload())


@dataclass(frozen=True, slots=True)
class VariableGraphAtomV1:
    ordinal: int
    next_state: VariableGraphStateV1
    probability: Fraction
    normalized_reward: Fraction
    failure: bool

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.next_state) is not VariableGraphStateV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable-order graph atom is invalid"
            )


@dataclass(frozen=True, slots=True)
class ObservedVariableGraphAtomV1:
    """Exact local support descriptor without an exact probability field."""

    ordinal: int
    next_state: VariableGraphStateV1
    normalized_reward: Fraction
    failure: bool

    def __post_init__(self) -> None:
        if (
            type(self.ordinal) is not int
            or self.ordinal < 0
            or type(self.next_state) is not VariableGraphStateV1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
        ):
            raise VariableOrderGraphInvariantViolation(
                "observed local-support atom is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "ordinal": self.ordinal,
            "next_state_id": self.next_state.state_id,
            "next_state_ranks": list(self.next_state.ranks),
            "failure": self.failure,
            "normalized_reward": _fdoc(self.normalized_reward),
        }


class RelationalGraphMergeKernelV2:
    """The V0-065 graph-merge equations lifted to dynamic graph order."""

    def __init__(self, context: VariableOrderGraphContextV1) -> None:
        if (
            type(context) is not VariableOrderGraphContextV1
            or context not in registered_variable_order_contexts_v1()
        ):
            raise VariableOrderGraphInvariantViolation(
                "dynamic kernel requires a registered context"
            )
        self.context = context

    def actions(
        self,
        state: VariableGraphStateV1,
    ) -> tuple[tuple[int, int, int], ...]:
        self._validate_state(state)
        if state.failure:
            return ()
        return tuple(
            (first, second, survivor)
            for first, second in self.context.topology.edges
            if state.ranks[first] > 0
            and state.ranks[first] == state.ranks[second]
            for survivor in (first, second)
        )

    def _validate_state(self, state: VariableGraphStateV1) -> None:
        if (
            type(state) is not VariableGraphStateV1
            or len(state.ranks) != self.context.vertex_count
        ):
            raise VariableOrderGraphInvariantViolation(
                "state is outside the dynamic graph context"
            )

    def atoms(
        self,
        state: VariableGraphStateV1,
        action: tuple[int, int, int],
    ) -> tuple[VariableGraphAtomV1, ...]:
        self._validate_state(state)
        if action not in self.actions(state):
            raise VariableOrderGraphInvariantViolation(
                "dynamic graph action is not legal"
            )
        first, second, survivor = action
        rank = state.ranks[first]
        board = list(state.ranks)
        board[first] = 0
        board[second] = 0
        board[survivor] = min(rank + 1, RANK_CAP)
        empty = tuple(index for index, value in enumerate(board) if value == 0)
        reward = (
            Fraction(2 ** (rank + 1), 2 ** (RANK_CAP + 1))
            / REWARD_NORMALIZER
        )
        atoms: list[VariableGraphAtomV1] = []
        for cell in empty:
            for spawn_rank, rank_probability in (
                (LOW_RANK, LOW_RANK_PROBABILITY),
                (LOW_RANK + 1, 1 - LOW_RANK_PROBABILITY),
            ):
                successor = board.copy()
                successor[cell] = spawn_rank
                provisional = VariableGraphStateV1(tuple(successor))
                failure = not self.actions(provisional)
                atoms.append(
                    VariableGraphAtomV1(
                        len(atoms),
                        VariableGraphStateV1(tuple(successor), failure),
                        Fraction(1, len(empty)) * rank_probability,
                        reward,
                        failure,
                    )
                )
        expected = 2 * (self.context.vertex_count - 2)
        if (
            len(atoms) != expected
            or sum((item.probability for item in atoms), Fraction(0)) != 1
        ):
            raise AssertionError("dynamic graph atom support changed")
        return tuple(atoms)

    def root_state(self) -> VariableGraphStateV1:
        return VariableGraphStateV1(self.context.root_board)


def _state_view(
    context: VariableOrderGraphContextV1,
    state: VariableGraphStateV1,
    remaining_horizon: int,
) -> GraphStateViewV1:
    return GraphStateViewV1(
        context.topology.topology_id,
        state.ranks,
        state.failure,
        remaining_horizon,
    )


@dataclass(frozen=True, slots=True)
class VariableGraphCatalogueV1:
    context_id: str
    state: VariableGraphStateV1
    remaining_horizon: int
    actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "catalogue context")
        if (
            type(self.state) is not VariableGraphStateV1
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.actions) is not tuple
            or not self.actions
            or any(
                type(item) is not tuple
                or len(item) != 3
                or any(type(value) is not int for value in item)
                for item in self.actions
            )
            or self.actions != tuple(sorted(set(self.actions)))
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable graph catalogue is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state_id": self.state.state_id,
            "state": list(self.state.ranks),
            "remaining_horizon": self.remaining_horizon,
            "actions": [list(item) for item in self.actions],
        }

    @property
    def catalogue_id(self) -> str:
        return _content_id("catalogue", self._payload())


def _catalogue(
    context: VariableOrderGraphContextV1,
    state: VariableGraphStateV1,
    remaining_horizon: int,
) -> VariableGraphCatalogueV1:
    kernel = RelationalGraphMergeKernelV2(context)
    return VariableGraphCatalogueV1(
        context.context_id,
        state,
        remaining_horizon,
        kernel.actions(state),
    )


def _splitmix64(value: int) -> int:
    value &= (1 << 64) - 1
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9
    value &= (1 << 64) - 1
    value = (value ^ (value >> 27)) * 0x94D049BB133111EB
    value &= (1 << 64) - 1
    return value ^ (value >> 31)


def _row_seed(
    context: VariableOrderGraphContextV1,
    catalogue: VariableGraphCatalogueV1,
    action: tuple[int, int, int],
) -> int:
    payload = canonical_json_bytes(
        {
            "profile_key": PROFILE_KEY,
            "sampling_context_id": context.sampling_context_id,
            "state_id": catalogue.state.state_id,
            "remaining_horizon": catalogue.remaining_horizon,
            "action": list(action),
            "sample_count": SAMPLE_COUNT_PER_ROW,
        }
    )
    return int.from_bytes(
        hashlib.sha256(
            b"acfqp:variable-order-graph-row-seed:v1\x00" + payload
        ).digest()[:8],
        "big",
    )


def exact_rejection_ordinal_v1(
    empty_cell_count: int,
    random_uint64: int,
) -> int | None:
    """Map one ideal-uniform uint64 exactly, rejecting the modulo tail.

    This removes finite-word modulo bias; it does *not* claim that SplitMix64
    is itself a source of IID entropy.  Statistical claims remain explicitly
    conditional on the registered simulator assumption.
    """

    if (
        type(empty_cell_count) is not int
        or empty_cell_count not in (3, 4)
        or type(random_uint64) is not int
        or not 0 <= random_uint64 < (1 << 64)
    ):
        raise VariableOrderGraphInvariantViolation(
            "exact rejection mapper received an invalid domain value"
        )
    outcome_count = 100 * empty_cell_count
    acceptance_limit = (1 << 64) - ((1 << 64) % outcome_count)
    if random_uint64 >= acceptance_limit:
        return None
    token = random_uint64 % outcome_count
    return 2 * (token // 100) + (0 if token % 100 < 99 else 1)


def _pack_rejection_flags(flags: Iterable[bool]) -> bytes:
    output = bytearray()
    byte = 0
    width = 0
    for flag in flags:
        if type(flag) is not bool:
            raise VariableOrderGraphInvariantViolation(
                "rejection trace contains a non-boolean flag"
            )
        if flag:
            byte |= 1 << width
        width += 1
        if width == 8:
            output.append(byte)
            byte = 0
            width = 0
    if width:
        output.append(byte)
    return bytes(output)


def _unpack_rejection_flags(
    packed: bytes,
    random_word_count: int,
) -> tuple[bool, ...]:
    if (
        type(packed) is not bytes
        or type(random_word_count) is not int
        or random_word_count <= 0
        or len(packed) != math.ceil(random_word_count / 8)
    ):
        raise VariableOrderGraphInvariantViolation(
            "packed rejection trace shape is invalid"
        )
    flags = tuple(
        bool((packed[index // 8] >> (index % 8)) & 1)
        for index in range(random_word_count)
    )
    trailing = random_word_count % 8
    if trailing and packed[-1] >> trailing:
        raise VariableOrderGraphInvariantViolation(
            "packed rejection trace has nonzero trailing bits"
        )
    return flags


def _pack_three_bit_ordinals(ordinals: Iterable[int]) -> bytes:
    output = bytearray()
    accumulator = 0
    bits = 0
    for ordinal in ordinals:
        if type(ordinal) is not int or not 0 <= ordinal < 8:
            raise VariableOrderGraphInvariantViolation(
                "three-bit ordinal is outside [0,8)"
            )
        accumulator |= ordinal << bits
        bits += 3
        while bits >= 8:
            output.append(accumulator & 0xFF)
            accumulator >>= 8
            bits -= 8
    if bits:
        output.append(accumulator)
    return bytes(output)


def _unpack_three_bit_ordinals(
    packed: bytes,
    sample_count: int,
    atom_count: int,
) -> tuple[int, ...]:
    if (
        type(packed) is not bytes
        or type(sample_count) is not int
        or sample_count <= 0
        or atom_count not in (6, 8)
        or len(packed) != math.ceil(3 * sample_count / 8)
    ):
        raise VariableOrderGraphInvariantViolation(
            "packed ordinal stream shape is invalid"
        )
    result: list[int] = []
    accumulator = 0
    bits = 0
    for byte in packed:
        accumulator |= byte << bits
        bits += 8
        while bits >= 3 and len(result) < sample_count:
            ordinal = accumulator & 7
            if ordinal >= atom_count:
                raise VariableOrderGraphInvariantViolation(
                    "packed stream contains an impossible atom ordinal"
                )
            result.append(ordinal)
            accumulator >>= 3
            bits -= 3
    if len(result) != sample_count or accumulator != 0:
        raise VariableOrderGraphInvariantViolation(
            "packed stream count or trailing bits changed"
        )
    return tuple(result)


@dataclass(frozen=True, slots=True)
class PackedVariableGraphRowV1:
    context_id: str
    catalogue: VariableGraphCatalogueV1
    action: tuple[int, int, int]
    atom_count: int
    sample_count: int
    random_word_count: int
    rejection_count: int
    atom_descriptors: tuple[ObservedVariableGraphAtomV1, ...]
    packed_ordinals: bytes
    packed_rejection_flags: bytes
    ordinal_counts: tuple[int, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "packed row context")
        if (
            type(self.catalogue) is not VariableGraphCatalogueV1
            or self.context_id != self.catalogue.context_id
            or self.action not in self.catalogue.actions
            or self.atom_count
            != 2 * (len(self.catalogue.state.ranks) - 2)
            or self.sample_count != SAMPLE_COUNT_PER_ROW
            or type(self.random_word_count) is not int
            or self.random_word_count < self.sample_count
            or type(self.rejection_count) is not int
            or self.rejection_count < 0
            or self.random_word_count
            != self.sample_count + self.rejection_count
            or type(self.atom_descriptors) is not tuple
            or len(self.atom_descriptors) != self.atom_count
            or any(
                type(item) is not ObservedVariableGraphAtomV1
                for item in self.atom_descriptors
            )
            or tuple(item.ordinal for item in self.atom_descriptors)
            != tuple(range(self.atom_count))
            or type(self.packed_ordinals) is not bytes
            or type(self.packed_rejection_flags) is not bytes
            or len(self.packed_rejection_flags)
            != math.ceil(self.random_word_count / 8)
            or type(self.ordinal_counts) is not tuple
            or len(self.ordinal_counts) != self.atom_count
            or any(type(item) is not int or item < 0 for item in self.ordinal_counts)
            or sum(self.ordinal_counts) != self.sample_count
        ):
            raise VariableOrderGraphInvariantViolation(
                "packed variable graph row is invalid"
            )

    def _identity_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_packed_row.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue.catalogue_id,
            "action": list(self.action),
            "atom_count": self.atom_count,
            "sample_count": self.sample_count,
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "atom_descriptors": [
                item.to_document() for item in self.atom_descriptors
            ],
            "ordinal_counts": list(self.ordinal_counts),
            "packed_sha256": hashlib.sha256(self.packed_ordinals).hexdigest(),
            "packed_byte_count": len(self.packed_ordinals),
            "rejection_trace_sha256": hashlib.sha256(
                self.packed_rejection_flags
            ).hexdigest(),
            "rejection_trace_byte_count": len(
                self.packed_rejection_flags
            ),
            "prng_semantics_id": REGISTERED_PRNG_SEMANTICS_ID,
            "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
        }

    @property
    def row_id(self) -> str:
        payload = canonical_json_bytes(self._identity_payload())
        return hashlib.sha256(
            DOMAIN_TAGS["row"].encode("utf-8")
            + b"\x00"
            + payload
            + b"\x00"
            + self.packed_ordinals
            + b"\x00"
            + self.packed_rejection_flags
        ).hexdigest()


def _acquire_row(
    context: VariableOrderGraphContextV1,
    catalogue: VariableGraphCatalogueV1,
    action: tuple[int, int, int],
) -> PackedVariableGraphRowV1:
    atom_count = 2 * (context.vertex_count - 2)
    exact_atoms = RelationalGraphMergeKernelV2(context).atoms(
        catalogue.state,
        action,
    )
    descriptors = tuple(
        ObservedVariableGraphAtomV1(
            item.ordinal,
            item.next_state,
            item.normalized_reward,
            item.failure,
        )
        for item in exact_atoms
    )
    seed = _row_seed(context, catalogue, action)
    gamma = 0x9E3779B97F4A7C15
    counts = [0] * atom_count
    ordinals: list[int] = []
    rejection_flags: list[bool] = []
    random_word_index = 0
    while len(ordinals) < SAMPLE_COUNT_PER_ROW:
        random_uint64 = _splitmix64(
            seed + gamma * (random_word_index + 1)
        )
        random_word_index += 1
        mapped = exact_rejection_ordinal_v1(
            atom_count // 2,
            random_uint64,
        )
        rejected = mapped is None
        rejection_flags.append(rejected)
        if rejected:
            continue
        ordinal = mapped
        counts[ordinal] += 1
        ordinals.append(ordinal)
    return PackedVariableGraphRowV1(
        context.context_id,
        catalogue,
        action,
        atom_count,
        SAMPLE_COUNT_PER_ROW,
        random_word_index,
        random_word_index - SAMPLE_COUNT_PER_ROW,
        descriptors,
        _pack_three_bit_ordinals(ordinals),
        _pack_rejection_flags(rejection_flags),
        tuple(counts),
    )


def verify_packed_variable_graph_row_v1(
    context: VariableOrderGraphContextV1,
    row: PackedVariableGraphRowV1,
) -> bool:
    if (
        type(context) is not VariableOrderGraphContextV1
        or type(row) is not PackedVariableGraphRowV1
        or row.context_id != context.context_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "packed-row replay binding is invalid"
        )
    decoded = _unpack_three_bit_ordinals(
        row.packed_ordinals,
        row.sample_count,
        row.atom_count,
    )
    counts = [0] * row.atom_count
    for ordinal in decoded:
        counts[ordinal] += 1
    if tuple(counts) != row.ordinal_counts:
        raise VariableOrderGraphInvariantViolation(
            "packed row counts do not match raw ordinals"
        )
    rejection_flags = _unpack_rejection_flags(
        row.packed_rejection_flags,
        row.random_word_count,
    )
    if sum(rejection_flags) != row.rejection_count:
        raise VariableOrderGraphInvariantViolation(
            "packed rejection count does not match its trace"
        )
    expected = _acquire_row(context, row.catalogue, row.action)
    if (
        expected.row_id != row.row_id
        or expected.packed_ordinals != row.packed_ordinals
        or expected.packed_rejection_flags != row.packed_rejection_flags
    ):
        raise VariableOrderGraphInvariantViolation(
            "packed row failed deterministic raw replay"
        )
    return True


class AccessKind(str, Enum):
    ROOT_CATALOGUE = "ROOT_CATALOGUE"
    ROOT_ROWS = "ROOT_ROWS"
    DIRECT_BAD_PRUNE = "DIRECT_BAD_PRUNE"
    CONCRETIZER_FREEZE = "CONCRETIZER_FREEZE"
    SELECTED_SUCCESSOR_CATALOGUES = "SELECTED_SUCCESSOR_CATALOGUES"
    CONTINUATION_ROWS = "CONTINUATION_ROWS"
    BASE_AUDIT = "BASE_AUDIT"
    TARGET_PROGRAM_GENERATION = "TARGET_PROGRAM_GENERATION"
    FINAL_AUDIT = "FINAL_AUDIT"


@dataclass(frozen=True, slots=True)
class SparseAccessEventV1:
    sequence: int
    kind: AccessKind
    ground_row_count_after: int
    complete_closure_accessed: bool = False
    source_registry_accessed: bool = False
    source_dynamics_accessed: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.sequence) is not int
            or self.sequence <= 0
            or type(self.kind) is not AccessKind
            or type(self.ground_row_count_after) is not int
            or self.ground_row_count_after < 0
            or self.complete_closure_accessed is not False
            or self.source_registry_accessed is not False
            or self.source_dynamics_accessed is not False
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse access event violates the operational boundary"
            )


@dataclass(frozen=True, slots=True)
class SparseAccessLogV1:
    context_id: str
    events: tuple[SparseAccessEventV1, ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "access-log context")
        if (
            type(self.events) is not tuple
            or not self.events
            or any(type(item) is not SparseAccessEventV1 for item in self.events)
            or tuple(item.sequence for item in self.events)
            != tuple(range(1, len(self.events) + 1))
            or any(
                left.ground_row_count_after > right.ground_row_count_after
                for left, right in zip(self.events, self.events[1:])
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse access sequence is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_access_log.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "events": [
                {
                    "sequence": item.sequence,
                    "kind": item.kind.value,
                    "ground_row_count_after": item.ground_row_count_after,
                    "complete_closure_accessed": False,
                    "source_registry_accessed": False,
                    "source_dynamics_accessed": False,
                }
                for item in self.events
            ],
        }

    @property
    def access_log_id(self) -> str:
        return _content_id("access", self._payload())


@dataclass(frozen=True, slots=True)
class RootConeAuthorizationV1:
    context_id: str
    skeleton_id: str
    root_catalogue_id: str
    root_row_ids: tuple[str, ...]
    selected_action_coordinate: tuple[tuple[str, Any], ...]
    selected_ground_actions: tuple[tuple[int, int, int], ...]
    immediate_failure_upper: Fraction
    authorization_sequence: int = 3

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "root authorization context"),
            (self.skeleton_id, "root authorization skeleton"),
            (self.root_catalogue_id, "root authorization catalogue"),
        ):
            _cid(value, field)
        for item in self.root_row_ids:
            _cid(item, "root authorization row")
        if (
            type(self.root_row_ids) is not tuple
            or len(self.root_row_ids) != 2
            or self.root_row_ids != tuple(sorted(set(self.root_row_ids)))
            or type(self.selected_action_coordinate) is not tuple
            or not self.selected_action_coordinate
            or type(self.selected_ground_actions) is not tuple
            or not self.selected_ground_actions
            or self.selected_ground_actions
            != tuple(sorted(set(self.selected_ground_actions)))
            or type(self.immediate_failure_upper) is not Fraction
            or not 0 <= self.immediate_failure_upper <= 1
            or self.authorization_sequence != 3
        ):
            raise VariableOrderGraphInvariantViolation(
                "root proof-cone authorization is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_root_cone_authorization.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "skeleton_id": self.skeleton_id,
            "root_catalogue_id": self.root_catalogue_id,
            "root_row_ids": list(self.root_row_ids),
            "selected_action_coordinate": _jsonable(
                self.selected_action_coordinate
            ),
            "selected_ground_actions": [
                list(item) for item in self.selected_ground_actions
            ],
            "immediate_failure_upper": _fdoc(
                self.immediate_failure_upper
            ),
            "authorization_sequence": self.authorization_sequence,
        }

    @property
    def authorization_id(self) -> str:
        return _content_id("authorization", self._payload())


@dataclass(frozen=True, slots=True)
class SparseVariableGraphEvidenceV1:
    context_id: str
    root_catalogue_id: str
    authorization: RootConeAuthorizationV1
    selected_root_action: tuple[int, int, int]
    selected_root_concretizer_actions: tuple[tuple[int, int, int], ...]
    root_rows: tuple[PackedVariableGraphRowV1, ...]
    continuation_catalogues: tuple[VariableGraphCatalogueV1, ...]
    continuation_rows: tuple[PackedVariableGraphRowV1, ...]
    access_log: SparseAccessLogV1
    preregistered_aggregate_obligation_count: int
    source_dynamics_rows_used: int = 0
    complete_target_closure_rows_used: int = 0

    def __post_init__(self) -> None:
        _cid(self.context_id, "sparse evidence context")
        _cid(self.root_catalogue_id, "sparse evidence root catalogue")
        if (
            type(self.authorization) is not RootConeAuthorizationV1
            or self.authorization.context_id != self.context_id
            or self.authorization.root_catalogue_id
            != self.root_catalogue_id
            or
            type(self.selected_root_action) is not tuple
            or type(self.selected_root_concretizer_actions) is not tuple
            or not self.selected_root_concretizer_actions
            or self.selected_root_action
            not in self.selected_root_concretizer_actions
            or self.selected_root_concretizer_actions
            != self.authorization.selected_ground_actions
            or type(self.root_rows) is not tuple
            or len(self.root_rows) != 2
            or type(self.continuation_catalogues) is not tuple
            or not self.continuation_catalogues
            or type(self.continuation_rows) is not tuple
            or not self.continuation_rows
            or any(
                type(item) is not PackedVariableGraphRowV1
                or item.context_id != self.context_id
                for item in self.root_rows + self.continuation_rows
            )
            or any(
                type(item) is not VariableGraphCatalogueV1
                or item.context_id != self.context_id
                or item.remaining_horizon != 1
                for item in self.continuation_catalogues
            )
            or tuple(item.row_id for item in self.root_rows)
            != tuple(sorted({item.row_id for item in self.root_rows}))
            or tuple(item.catalogue_id for item in self.continuation_catalogues)
            != tuple(
                sorted(
                    {item.catalogue_id for item in self.continuation_catalogues}
                )
            )
            or tuple(item.row_id for item in self.continuation_rows)
            != tuple(
                sorted({item.row_id for item in self.continuation_rows})
            )
            or type(self.access_log) is not SparseAccessLogV1
            or self.access_log.context_id != self.context_id
            or self.access_log.events[-1].ground_row_count_after
            != self.ground_row_count
            or type(self.preregistered_aggregate_obligation_count) is not int
            or self.preregistered_aggregate_obligation_count <= 0
            or self.source_dynamics_rows_used != 0
            or self.complete_target_closure_rows_used != 0
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse evidence identity, ordering, or chronology changed"
            )
        catalogue_ids = {
            item.catalogue_id for item in self.continuation_catalogues
        }
        if {
            item.catalogue.catalogue_id for item in self.continuation_rows
        } != catalogue_ids:
            raise VariableOrderGraphInvariantViolation(
                "continuation evidence does not exactly cover its sparse catalogues"
            )
        rows_by_catalogue: dict[str, set[tuple[int, int, int]]] = defaultdict(set)
        for row in self.continuation_rows:
            rows_by_catalogue[row.catalogue.catalogue_id].add(row.action)
        if any(
            rows_by_catalogue[item.catalogue_id] != set(item.actions)
            for item in self.continuation_catalogues
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse continuation catalogue omits a legal ground row"
            )

    @property
    def ground_row_count(self) -> int:
        return len(self.root_rows) + len(self.continuation_rows)

    @property
    def generative_draw_count(self) -> int:
        return self.ground_row_count * SAMPLE_COUNT_PER_ROW

    @property
    def atom_obligation_count(self) -> int:
        return sum(
            item.atom_count for item in self.root_rows + self.continuation_rows
        )

    @property
    def exact_local_support_row_count(self) -> int:
        return self.ground_row_count

    @property
    def random_word_count(self) -> int:
        return sum(
            item.random_word_count
            for item in self.root_rows + self.continuation_rows
        )

    @property
    def rejection_count(self) -> int:
        return sum(
            item.rejection_count
            for item in self.root_rows + self.continuation_rows
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_sparse_evidence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "root_catalogue_id": self.root_catalogue_id,
            "authorization_id": self.authorization.authorization_id,
            "selected_root_action": list(self.selected_root_action),
            "selected_root_concretizer_actions": [
                list(item) for item in self.selected_root_concretizer_actions
            ],
            "root_row_ids": [item.row_id for item in self.root_rows],
            "continuation_catalogue_ids": [
                item.catalogue_id for item in self.continuation_catalogues
            ],
            "continuation_row_ids": [
                item.row_id for item in self.continuation_rows
            ],
            "access_log_id": self.access_log.access_log_id,
            "ground_row_count": self.ground_row_count,
            "generative_draw_count": self.generative_draw_count,
            "atom_obligation_count": self.atom_obligation_count,
            "preregistered_aggregate_obligation_count": (
                self.preregistered_aggregate_obligation_count
            ),
            "exact_local_support_row_count": (
                self.exact_local_support_row_count
            ),
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "source_dynamics_rows_used": 0,
            "complete_target_closure_rows_used": 0,
        }

    @property
    def evidence_id(self) -> str:
        return _content_id("evidence", self._payload())


def _authorize_root_cone(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
    root_catalogue: VariableGraphCatalogueV1,
    root_rows: tuple[PackedVariableGraphRowV1, ...],
) -> RootConeAuthorizationV1:
    """Select a semantic root action only after both root rows exist."""

    state_ir = _target_state_ir(context, root_catalogue.state, HORIZON)
    rows_by_action = {item.action: item for item in root_rows}
    grouped: dict[
        tuple[tuple[str, Any], ...],
        list[tuple[tuple[int, int, int], Fraction]],
    ] = defaultdict(list)
    for action in root_catalogue.actions:
        slot = _profile_action_slot(state_ir, action)
        coordinate = (
            evaluate_portable_action_program_v1(
                skeleton.action_program,
                state_ir,
                slot,
            ),
        )
        row = rows_by_action[action]
        failures = sum(
            row.ordinal_counts[atom.ordinal]
            for atom in row.atom_descriptors
            if atom.failure
        )
        grouped[coordinate].append(
            (
                action,
                min(
                    Fraction(1),
                    Fraction(failures, row.sample_count)
                    + HOEFFDING_RADIUS,
                ),
            )
        )
    summaries = tuple(
        (
            coordinate,
            tuple(sorted(action for action, _ in members)),
            sum((upper for _, upper in members), Fraction(0))
            / len(members),
        )
        for coordinate, members in grouped.items()
    )
    coordinate, actions, upper = min(
        summaries,
        key=lambda item: (item[2], repr(item[0])),
    )
    return RootConeAuthorizationV1(
        context.context_id,
        skeleton.skeleton_id,
        root_catalogue.catalogue_id,
        tuple(sorted(item.row_id for item in root_rows)),
        coordinate,
        actions,
        upper,
    )


def _preregistered_aggregate_obligation_count(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
    rows: tuple[PackedVariableGraphRowV1, ...],
) -> int:
    """Count every grammar-reachable aggregate event before candidate choice."""

    extras = tuple(
        item
        for item in syntactic_portable_program_closure_v1()
        if item.context is RelationalProgramContext.STATE
        and item.result_type
        in (RelationalProgramType.INTEGER, RelationalProgramType.SIGNATURE)
        and item.program_id != skeleton.state_program.program_id
    )
    program_sets = ((skeleton.state_program,),) + tuple(
        (skeleton.state_program, item) for item in extras
    )
    total = 0
    for row in rows:
        subsets: set[frozenset[int]] = set()
        for programs in program_sets:
            grouped: dict[tuple[Any, ...], set[int]] = defaultdict(set)
            for atom in row.atom_descriptors:
                if atom.failure:
                    destination = ("FAILURE",)
                elif row.catalogue.remaining_horizon == 1:
                    destination = ("SAFE_TERMINAL",)
                else:
                    state_ir = _target_state_ir(
                        context,
                        atom.next_state,
                        row.catalogue.remaining_horizon - 1,
                    )
                    destination = (
                        "ACTIVE",
                        *(
                            evaluate_portable_state_program_v1(
                                program,
                                state_ir,
                            )
                            for program in programs
                        ),
                    )
                grouped[destination].add(atom.ordinal)
            subsets.update(
                frozenset(items)
                for items in grouped.values()
                if 0 < len(items) < row.atom_count
            )
        total += len(subsets)
    if total <= 0:
        raise VariableOrderGraphInvariantViolation(
            "preregistered aggregate obligation family is empty"
        )
    return total


@functools.lru_cache(maxsize=3)
def acquire_sparse_variable_graph_evidence_v1(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
) -> SparseVariableGraphEvidenceV1:
    """Acquire only the proof-cone rows for one registered root occurrence."""

    if (
        type(context) is not VariableOrderGraphContextV1
        or context not in registered_variable_order_contexts_v1()
        or type(skeleton) is not PortableRelationalSkeletonV1
    ):
        raise VariableOrderGraphInvariantViolation(
            "sparse acquisition requires a registered target"
        )
    root = RelationalGraphMergeKernelV2(context).root_state()
    root_catalogue = _catalogue(context, root, HORIZON)
    if len(root_catalogue.actions) != 2:
        raise AssertionError("registered root must have two survivor actions")
    root_rows = tuple(
        sorted(
            (
                _acquire_row(context, root_catalogue, action)
                for action in root_catalogue.actions
            ),
            key=lambda item: item.row_id,
        )
    )
    authorization = _authorize_root_cone(
        context,
        skeleton,
        root_catalogue,
        root_rows,
    )
    concretizer_actions = authorization.selected_ground_actions
    successors = {
        atom.next_state
        for action in concretizer_actions
        for row in root_rows
        if row.action == action
        for atom in row.atom_descriptors
        if not atom.failure
    }
    continuations = tuple(
        sorted(
            (
                _catalogue(context, state, 1)
                for state in successors
            ),
            key=lambda item: item.catalogue_id,
        )
    )
    continuation_rows = tuple(
        sorted(
            (
                _acquire_row(context, catalogue, action)
                for catalogue in continuations
                for action in catalogue.actions
            ),
            key=lambda item: item.row_id,
        )
    )
    after_root = len(root_rows)
    final_count = after_root + len(continuation_rows)
    third_kind = (
        AccessKind.CONCRETIZER_FREEZE
        if len(concretizer_actions) > 1
        else AccessKind.DIRECT_BAD_PRUNE
    )
    access_log = SparseAccessLogV1(
        context.context_id,
        (
            SparseAccessEventV1(1, AccessKind.ROOT_CATALOGUE, 0),
            SparseAccessEventV1(2, AccessKind.ROOT_ROWS, after_root),
            SparseAccessEventV1(3, third_kind, after_root),
            SparseAccessEventV1(
                4,
                AccessKind.SELECTED_SUCCESSOR_CATALOGUES,
                after_root,
            ),
            SparseAccessEventV1(
                5,
                AccessKind.CONTINUATION_ROWS,
                final_count,
            ),
        ),
    )
    return SparseVariableGraphEvidenceV1(
        context.context_id,
        root_catalogue.catalogue_id,
        authorization,
        concretizer_actions[0],
        concretizer_actions,
        root_rows,
        continuations,
        continuation_rows,
        access_log,
        _preregistered_aggregate_obligation_count(
            context,
            skeleton,
            root_rows + continuation_rows,
        ),
    )


@dataclass(frozen=True, slots=True)
class SparseEvidenceVerificationV1:
    context_id: str
    evidence_id: str
    replayed_ground_rows: int
    replayed_draws: int
    raw_replay_passed: bool
    sparse_chronology_passed: bool

    def __post_init__(self) -> None:
        _cid(self.context_id, "evidence-verification context")
        _cid(self.evidence_id, "evidence-verification evidence")
        if (
            type(self.replayed_ground_rows) is not int
            or self.replayed_ground_rows <= 0
            or self.replayed_draws
            != self.replayed_ground_rows * SAMPLE_COUNT_PER_ROW
            or self.raw_replay_passed is not True
            or self.sparse_chronology_passed is not True
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse evidence verification is incomplete"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_evidence_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "evidence_id": self.evidence_id,
            "replayed_ground_rows": self.replayed_ground_rows,
            "replayed_draws": self.replayed_draws,
            "raw_replay_passed": True,
            "sparse_chronology_passed": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("verification", self._payload())


def verify_sparse_variable_graph_evidence_v1(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
    evidence: SparseVariableGraphEvidenceV1,
) -> SparseEvidenceVerificationV1:
    if (
        type(evidence) is not SparseVariableGraphEvidenceV1
        or evidence.context_id != context.context_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "sparse evidence replay binding is invalid"
        )
    expected = acquire_sparse_variable_graph_evidence_v1(context, skeleton)
    if evidence.evidence_id != expected.evidence_id:
        raise VariableOrderGraphInvariantViolation(
            "sparse evidence identity failed replay"
        )
    for row in evidence.root_rows + evidence.continuation_rows:
        verify_packed_variable_graph_row_v1(context, row)
    return SparseEvidenceVerificationV1(
        context.context_id,
        evidence.evidence_id,
        evidence.ground_row_count,
        evidence.generative_draw_count,
        True,
        True,
    )


@dataclass(frozen=True, slots=True)
class GroundPolicyAssignmentV1:
    state: VariableGraphStateV1
    remaining_horizon: int
    action: tuple[int, int, int]
    failure_probability: Fraction
    normalized_reward: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.state) is not VariableGraphStateV1
            or self.state.failure
            or self.remaining_horizon not in (1, HORIZON)
            or type(self.action) is not tuple
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
        ):
            raise VariableOrderGraphInvariantViolation(
                "exact ground policy assignment is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state.state_id,
            "state_ranks": list(self.state.ranks),
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "failure_probability": _fdoc(self.failure_probability),
            "normalized_reward": _fdoc(self.normalized_reward),
        }


@dataclass(frozen=True, slots=True)
class _ExactGroundSearchV1:
    context_id: str
    assignments: tuple[GroundPolicyAssignmentV1, ...]
    root_failure_probability: Fraction
    root_normalized_reward: Fraction
    evaluated_state_action_rows: int
    root_action_rows: int


def _exact_ground_search_v1(
    context: VariableOrderGraphContextV1,
) -> _ExactGroundSearchV1:
    kernel = RelationalGraphMergeKernelV2(context)
    memo: dict[
        tuple[str, int],
        tuple[Fraction, Fraction, tuple[int, int, int]],
    ] = {}
    states: dict[tuple[str, int], VariableGraphStateV1] = {}
    evaluated: set[tuple[str, int, tuple[int, int, int]]] = set()

    def solve(
        state: VariableGraphStateV1,
        remaining: int,
    ) -> tuple[Fraction, Fraction, tuple[int, int, int]]:
        key = (state.state_id, remaining)
        if key in memo:
            return memo[key]
        actions = kernel.actions(state)
        if remaining <= 0 or not actions:
            raise VariableOrderGraphInvariantViolation(
                "exact query search reached an unmarked dead state"
            )
        candidates: list[
            tuple[Fraction, Fraction, tuple[int, int, int]]
        ] = []
        for action in actions:
            evaluated.add((state.state_id, remaining, action))
            atoms = kernel.atoms(state, action)
            immediate = atoms[0].normalized_reward
            if any(atom.normalized_reward != immediate for atom in atoms):
                raise VariableOrderGraphInvariantViolation(
                    "exact row reward is not deterministic"
                )
            risk = Fraction(0)
            future_reward = Fraction(0)
            for atom in atoms:
                if atom.failure:
                    risk += atom.probability
                elif remaining > 1:
                    child_risk, child_reward, _ = solve(
                        atom.next_state,
                        remaining - 1,
                    )
                    risk += atom.probability * child_risk
                    future_reward += atom.probability * child_reward
            candidates.append((risk, immediate + future_reward, action))
        chosen = min(
            candidates,
            key=lambda item: (item[0], -item[1], item[2]),
        )
        memo[key] = chosen
        states[key] = state
        return chosen

    root = kernel.root_state()
    root_risk, root_reward, _ = solve(root, HORIZON)
    assignments = tuple(
        sorted(
            (
                GroundPolicyAssignmentV1(
                    states[key],
                    key[1],
                    value[2],
                    value[0],
                    value[1],
                )
                for key, value in memo.items()
            ),
            key=lambda item: (
                -item.remaining_horizon,
                item.state.state_id,
            ),
        )
    )
    return _ExactGroundSearchV1(
        context.context_id,
        assignments,
        root_risk,
        root_reward,
        len(evaluated),
        len(kernel.actions(root)),
    )


@dataclass(frozen=True, slots=True)
class ExactGroundFallbackProofV1:
    context_id: str
    failed_audit_id: str
    policy_assignments: tuple[GroundPolicyAssignmentV1, ...]
    exact_failure_probability: Fraction
    exact_normalized_reward: Fraction
    evaluated_state_action_rows: int
    complete_matched_query_search: bool = True
    optimization_scope: str = (
        "SPECIALIZED_EXACT_RISK_MIN_FEASIBLE_REGISTERED_H2_FAMILY"
    )

    def __post_init__(self) -> None:
        _cid(self.context_id, "fallback context")
        _cid(self.failed_audit_id, "fallback failed audit")
        if (
            type(self.policy_assignments) is not tuple
            or not self.policy_assignments
            or any(
                type(item) is not GroundPolicyAssignmentV1
                for item in self.policy_assignments
            )
            or type(self.exact_failure_probability) is not Fraction
            or not 0 <= self.exact_failure_probability <= 1
            or type(self.exact_normalized_reward) is not Fraction
            or not 0 <= self.exact_normalized_reward <= 1
            or type(self.evaluated_state_action_rows) is not int
            or self.evaluated_state_action_rows <= 0
            or self.complete_matched_query_search is not True
            or self.optimization_scope
            != "SPECIALIZED_EXACT_RISK_MIN_FEASIBLE_REGISTERED_H2_FAMILY"
        ):
            raise VariableOrderGraphInvariantViolation(
                "exact ground fallback proof is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_exact_fallback_proof.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "failed_audit_id": self.failed_audit_id,
            "policy_assignments": [
                item.to_document() for item in self.policy_assignments
            ],
            "exact_failure_probability": _fdoc(
                self.exact_failure_probability
            ),
            "exact_normalized_reward": _fdoc(
                self.exact_normalized_reward
            ),
            "evaluated_state_action_rows": (
                self.evaluated_state_action_rows
            ),
            "complete_matched_query_search": True,
            "optimization_scope": self.optimization_scope,
        }

    @property
    def proof_id(self) -> str:
        return _content_id("fallback", self._payload())


def execute_exact_ground_fallback_v1(
    context: VariableOrderGraphContextV1,
    failed_audit: PortableGraphAuditV1,
) -> ExactGroundFallbackProofV1:
    if (
        type(failed_audit) is not PortableGraphAuditV1
        or failed_audit.context_id != context.context_id
        or failed_audit.outcome
        is not PortableGraphAuditOutcome.FAILED_RISK_OR_ALIAS
    ):
        raise VariableOrderGraphInvariantViolation(
            "ground fallback requires the current failed abstract proof"
        )
    search = _exact_ground_search_v1(context)
    if search.root_failure_probability >= context.risk_tolerance:
        raise VariableOrderGraphInvariantViolation(
            "registered ground fallback did not find a feasible plan"
        )
    if search.root_normalized_reward != _registered_query_reward_ceiling(
        context
    ):
        raise VariableOrderGraphInvariantViolation(
            "registered risk-min fallback did not attain the reward ceiling"
        )
    return ExactGroundFallbackProofV1(
        context.context_id,
        failed_audit.audit_id,
        search.assignments,
        search.root_failure_probability,
        search.root_normalized_reward,
        search.evaluated_state_action_rows,
    )


@dataclass(frozen=True, slots=True)
class VariableGraphColdControlV1:
    context_id: str
    matched_root_count: int
    matched_root_row_count: int
    matched_continuation_row_count: int
    matched_h2_row_count: int
    exact_root_failure_probability: Fraction
    selected_exact_reward: Fraction
    evaluation_lane: str = "EVALUATION_ONLY"
    optimization_scope: str = (
        "MATCHED_SPECIALIZED_RISK_MIN_REGISTERED_H2_FAMILY"
    )

    def __post_init__(self) -> None:
        _cid(self.context_id, "cold-control context")
        if (
            any(
                type(item) is not int or item <= 0
                for item in (
                    self.matched_root_count,
                    self.matched_root_row_count,
                    self.matched_continuation_row_count,
                    self.matched_h2_row_count,
                )
            )
            or self.matched_root_count != 1
            or self.matched_h2_row_count
            != self.matched_root_row_count
            + self.matched_continuation_row_count
            or type(self.exact_root_failure_probability) is not Fraction
            or not 0 <= self.exact_root_failure_probability <= 1
            or self.selected_exact_reward != Fraction(3, 64)
            or self.evaluation_lane != "EVALUATION_ONLY"
            or self.optimization_scope
            != "MATCHED_SPECIALIZED_RISK_MIN_REGISTERED_H2_FAMILY"
        ):
            raise VariableOrderGraphInvariantViolation(
                "cold exact control is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_cold_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "matched_root_count": self.matched_root_count,
            "matched_root_row_count": self.matched_root_row_count,
            "matched_continuation_row_count": (
                self.matched_continuation_row_count
            ),
            "matched_h2_row_count": self.matched_h2_row_count,
            "exact_root_failure_probability": _fdoc(
                self.exact_root_failure_probability
            ),
            "selected_exact_reward": _fdoc(self.selected_exact_reward),
            "evaluation_lane": self.evaluation_lane,
            "optimization_scope": self.optimization_scope,
        }

    @property
    def control_id(self) -> str:
        return _content_id("cold", self._payload())


@functools.lru_cache(maxsize=3)
def cold_variable_graph_control_v1(
    context: VariableOrderGraphContextV1,
) -> VariableGraphColdControlV1:
    search = _exact_ground_search_v1(context)
    return VariableGraphColdControlV1(
        context.context_id,
        1,
        search.root_action_rows,
        search.evaluated_state_action_rows - search.root_action_rows,
        search.evaluated_state_action_rows,
        search.root_failure_probability,
        search.root_normalized_reward,
    )


def _action_key(action: tuple[int, int, int]) -> str:
    return f"merge:{action[0]}:{action[1]}:{action[2]}"


def _slot(action: tuple[int, int, int]) -> RelationalActionSlotV1:
    return RelationalActionSlotV1(_action_key(action), action[2])


def _oriented_links(
    topology: GraphTopologyV1,
) -> tuple[tuple[int, int], ...]:
    return tuple(
        sorted(
            (anchor, resource)
            for first, second in topology.edges
            for anchor, resource in ((first, second), (second, first))
        )
    )


def _relational_state_ir(
    structural_context_id: str,
    topology: GraphTopologyV1,
    ranks: tuple[int, ...],
    remaining_horizon: int,
    failure: bool,
    actions: tuple[tuple[int, int, int], ...],
) -> RelationalStateIRV1:
    if failure:
        terminal_kind = "FAILURE"
        slots: tuple[RelationalActionSlotV1, ...] = ()
    elif remaining_horizon == 0:
        terminal_kind = "HORIZON_TERMINAL"
        slots = ()
    else:
        terminal_kind = "ACTIVE"
        slots = tuple(
            sorted((_slot(item) for item in actions), key=lambda item: item.action_slot_id)
        )
    return RelationalStateIRV1(
        structural_context_id,
        remaining_horizon,
        ranks,
        tuple(index for index, rank in enumerate(ranks) if rank > 0),
        _oriented_links(topology),
        slots,
        terminal_kind,
    )


def _source_context_by_topology_id() -> dict[str, CrossGraphStructuralContextV1]:
    return {
        item.topology.topology_id: item
        for item in registered_cross_graph_contexts_v1()
        if item.context_key.startswith("cross_source_")
    }


def _canonical_relational_outcomes(
    rows: Iterable[
        tuple[
            RelationalStateIRV1,
            Fraction,
            Fraction,
            bool,
            bool,
        ]
    ],
) -> tuple[RelationalOutcomeIRV1, ...]:
    grouped: dict[
        tuple[str, Fraction, bool, bool],
        tuple[RelationalStateIRV1, Fraction],
    ] = {}
    for next_state, probability, reward, failure, terminal in rows:
        key = (next_state.state_ir_id, reward, failure, terminal)
        prior = grouped.get(key)
        grouped[key] = (
            next_state,
            probability if prior is None else prior[1] + probability,
        )
    outcomes = tuple(
        RelationalOutcomeIRV1(
            state,
            probability,
            key[1],
            key[2],
            key[3],
        )
        for key, (state, probability) in grouped.items()
    )
    return tuple(sorted(outcomes, key=lambda item: item.outcome_ir_id))


@functools.lru_cache(maxsize=1)
def portable_graph_source_log_v1() -> AnonymousRelationalObservationLogV1:
    """Adapt the frozen n=4 source observations into the generic role IR."""

    bundle = acquire_cross_graph_source_observations_v1()
    contexts = _source_context_by_topology_id()
    rows: list[RelationalObservedRowV1] = []
    for observed in bundle.observation_log.rows:
        context = contexts[observed.state.topology_id]
        actions = tuple(
            (item.first, item.second, item.survivor)
            for item in observed.legal_actions
        )
        state = _relational_state_ir(
            context.context_id,
            context.topology,
            observed.state.ranks,
            observed.state.remaining_horizon,
            observed.state.failure,
            actions,
        )
        slot_by_key = {
            item.opaque_action_key: item for item in state.legal_actions
        }
        action_tuple = (
            observed.action.first,
            observed.action.second,
            observed.action.survivor,
        )
        outcomes: list[
            tuple[RelationalStateIRV1, Fraction, Fraction, bool, bool]
        ] = []
        for outcome in observed.outcomes:
            next_actions: tuple[tuple[int, int, int], ...] = ()
            # Source outcome views do not carry the successor action catalogue.
            # Recompute it from graph incidence; no kernel probability is read.
            if (
                not outcome.next_state.failure
                and outcome.next_state.remaining_horizon > 0
            ):
                next_actions = tuple(
                    (first, second, survivor)
                    for first, second in context.topology.edges
                    if outcome.next_state.ranks[first] > 0
                    and outcome.next_state.ranks[first]
                    == outcome.next_state.ranks[second]
                    for survivor in (first, second)
                )
            next_state = _relational_state_ir(
                context.context_id,
                context.topology,
                outcome.next_state.ranks,
                outcome.next_state.remaining_horizon,
                outcome.failure,
                next_actions,
            )
            outcomes.append(
                (
                    next_state,
                    outcome.probability,
                    outcome.normalized_reward,
                    outcome.failure,
                    outcome.failure
                    or outcome.next_state.remaining_horizon == 0,
                )
            )
        rows.append(
            RelationalObservedRowV1(
                state,
                slot_by_key[_action_key(action_tuple)],
                _canonical_relational_outcomes(outcomes),
            )
        )
    return AnonymousRelationalObservationLogV1(
        PortableRelationalRoleSchemaV1(),
        tuple(sorted(rows, key=lambda item: item.observed_row_id)),
    )


def build_portable_graph_source_log_v1(
) -> AnonymousRelationalObservationLogV1:
    """Public data-only n=4 source projection shared by both V0-066 arms."""

    return portable_graph_source_log_v1()


@functools.lru_cache(maxsize=1)
def portable_graph_source_skeleton_v1() -> PortableRelationalSkeletonV1:
    log = portable_graph_source_log_v1()
    skeleton = synthesize_portable_relational_skeleton_v1(log)
    verify_portable_relational_skeleton_v1(log, skeleton)
    return skeleton


def portable_graph_source_metrics_v1(
) -> PortableRelationalSynthesisMetricsV1:
    return portable_relational_synthesis_metrics_v1(
        portable_graph_source_log_v1(),
        portable_graph_source_skeleton_v1(),
    )


def _target_state_ir(
    context: VariableOrderGraphContextV1,
    state: VariableGraphStateV1,
    remaining_horizon: int,
) -> RelationalStateIRV1:
    actions = (
        ()
        if state.failure or remaining_horizon == 0
        else RelationalGraphMergeKernelV2(context).actions(state)
    )
    return _relational_state_ir(
        context.context_id,
        context.topology,
        state.ranks,
        remaining_horizon,
        state.failure,
        actions,
    )


def _target_observed_row(
    context: VariableOrderGraphContextV1,
    row: PackedVariableGraphRowV1,
) -> RelationalObservedRowV1:
    state = _target_state_ir(
        context,
        row.catalogue.state,
        row.catalogue.remaining_horizon,
    )
    slots = {item.opaque_action_key: item for item in state.legal_actions}
    outcomes = _canonical_relational_outcomes(
        (
            (
                _target_state_ir(
                    context,
                    atom.next_state,
                    row.catalogue.remaining_horizon - 1,
                ),
                Fraction(row.ordinal_counts[atom.ordinal], row.sample_count),
                atom.normalized_reward,
                atom.failure,
                atom.failure or row.catalogue.remaining_horizon == 1,
            )
            for atom in row.atom_descriptors
            if row.ordinal_counts[atom.ordinal] > 0
        )
    )
    return RelationalObservedRowV1(
        state,
        slots[_action_key(row.action)],
        outcomes,
    )


def target_relational_observation_log_v1(
    context: VariableOrderGraphContextV1,
    evidence: SparseVariableGraphEvidenceV1,
) -> AnonymousRelationalObservationLogV1:
    if evidence.context_id != context.context_id:
        raise VariableOrderGraphInvariantViolation(
            "target observation-log evidence is foreign"
        )
    rows = tuple(
        sorted(
            (
                _target_observed_row(context, item)
                for item in evidence.root_rows + evidence.continuation_rows
            ),
            key=lambda item: item.observed_row_id,
        )
    )
    return AnonymousRelationalObservationLogV1(
        PortableRelationalRoleSchemaV1(),
        rows,
    )


TaggedCoordinate = tuple[tuple[str, Any], ...]
DestinationKey = tuple[Any, ...]


def _jsonable(value: Any) -> Any:
    if type(value) is tuple:
        return [_jsonable(item) for item in value]
    if type(value) is dict:
        return {str(key): _jsonable(item) for key, item in value.items()}
    return value


@dataclass(frozen=True, slots=True)
class PortableGraphCoordinateProfileV1:
    skeleton_id: str
    state_programs: tuple[PortableRelationalProgramV1, ...]
    action_programs: tuple[PortableRelationalProgramV1, ...]
    refinement_index: int
    generation_id: str | None
    failed_audit_id: str | None

    def __post_init__(self) -> None:
        _cid(self.skeleton_id, "coordinate-profile skeleton")
        if (
            type(self.state_programs) is not tuple
            or not self.state_programs
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE
                for item in self.state_programs
            )
            or type(self.action_programs) is not tuple
            or not self.action_programs
            or any(
                type(item) is not PortableRelationalProgramV1
                or item.context is not RelationalProgramContext.STATE_ACTION
                for item in self.action_programs
            )
            or len({item.program_id for item in self.state_programs})
            != len(self.state_programs)
            or len({item.program_id for item in self.action_programs})
            != len(self.action_programs)
            or self.refinement_index not in (0, 1)
            or (
                self.refinement_index == 0
                and (
                    len(self.state_programs) != 1
                    or len(self.action_programs) != 1
                    or self.generation_id is not None
                    or self.failed_audit_id is not None
                )
            )
            or (
                self.refinement_index == 1
                and (
                    len(self.state_programs) not in (1, 2)
                    or len(self.action_programs) not in (1, 2)
                    or len(self.state_programs) + len(self.action_programs)
                    <= 2
                    or self.generation_id is None
                    or self.failed_audit_id is None
                )
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "portable graph coordinate profile is invalid"
            )
        if self.generation_id is not None:
            _cid(self.generation_id, "coordinate-profile generation")
        if self.failed_audit_id is not None:
            _cid(self.failed_audit_id, "coordinate-profile failed audit")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_coordinate_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "state_programs": [
                item.to_document() for item in self.state_programs
            ],
            "action_programs": [
                item.to_document() for item in self.action_programs
            ],
            "refinement_index": self.refinement_index,
            "generation_id": self.generation_id,
            "failed_audit_id": self.failed_audit_id,
        }

    @property
    def profile_id(self) -> str:
        return _content_id("profile", self._payload())


def _base_coordinate_profile(
    skeleton: PortableRelationalSkeletonV1,
) -> PortableGraphCoordinateProfileV1:
    return PortableGraphCoordinateProfileV1(
        skeleton.skeleton_id,
        (skeleton.state_program,),
        (skeleton.action_program,),
        0,
        None,
        None,
    )


def _state_coordinate(
    profile: PortableGraphCoordinateProfileV1,
    state: RelationalStateIRV1,
) -> TaggedCoordinate:
    return tuple(
        evaluate_portable_state_program_v1(program, state)
        for program in profile.state_programs
    )


def _action_coordinate(
    profile: PortableGraphCoordinateProfileV1,
    state: RelationalStateIRV1,
    action: RelationalActionSlotV1,
) -> TaggedCoordinate:
    return tuple(
        evaluate_portable_action_program_v1(program, state, action)
        for program in profile.action_programs
    )


def _profile_state_ir(
    context: VariableOrderGraphContextV1,
    catalogue: VariableGraphCatalogueV1,
) -> RelationalStateIRV1:
    return _target_state_ir(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )


def _profile_action_slot(
    state: RelationalStateIRV1,
    action: tuple[int, int, int],
) -> RelationalActionSlotV1:
    key = _action_key(action)
    for slot in state.legal_actions:
        if slot.opaque_action_key == key:
            return slot
    raise VariableOrderGraphInvariantViolation(
        "ground action is absent from its relational state IR"
    )


def _support_key(
    profile: PortableGraphCoordinateProfileV1,
    context: VariableOrderGraphContextV1,
    catalogue: VariableGraphCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[int, TaggedCoordinate, TaggedCoordinate]:
    state = _profile_state_ir(context, catalogue)
    slot = _profile_action_slot(state, action)
    return (
        catalogue.remaining_horizon,
        _state_coordinate(profile, state),
        _action_coordinate(profile, state, slot),
    )


@dataclass(frozen=True, slots=True)
class StatisticalDestinationIntervalV1:
    destination: DestinationKey
    lower: Fraction
    upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.destination) is not tuple
            or not self.destination
            or self.destination[0] not in (
                "FAILURE",
                "SAFE_TERMINAL",
                "ACTIVE",
            )
            or type(self.lower) is not Fraction
            or type(self.upper) is not Fraction
            or not 0 <= self.lower <= self.upper <= 1
        ):
            raise VariableOrderGraphInvariantViolation(
                "statistical destination interval is invalid"
            )


@dataclass(frozen=True, slots=True)
class PartialRAPMRowV1:
    support_key: tuple[int, TaggedCoordinate, TaggedCoordinate]
    intervals: tuple[StatisticalDestinationIntervalV1, ...]
    reward_lower: Fraction
    reward_upper: Fraction
    ground_row_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            type(self.support_key) is not tuple
            or len(self.support_key) != 3
            or type(self.intervals) is not tuple
            or not self.intervals
            or any(
                type(item) is not StatisticalDestinationIntervalV1
                for item in self.intervals
            )
            or tuple(item.destination for item in self.intervals)
            != tuple(
                sorted(
                    {item.destination for item in self.intervals},
                    key=repr,
                )
            )
            or sum(
                (item.lower for item in self.intervals),
                Fraction(0),
            )
            > 1
            or sum(
                (item.upper for item in self.intervals),
                Fraction(0),
            )
            < 1
            or type(self.reward_lower) is not Fraction
            or type(self.reward_upper) is not Fraction
            or not 0 <= self.reward_lower <= self.reward_upper <= 1
            or self.ground_row_ids
            != tuple(sorted(set(self.ground_row_ids)))
            or not self.ground_row_ids
        ):
            raise VariableOrderGraphInvariantViolation(
                "partial RAPM row is invalid"
            )
        for item in self.ground_row_ids:
            _cid(item, "partial RAPM ground row")

    def to_document(self) -> dict[str, Any]:
        return {
            "support_key": _jsonable(self.support_key),
            "intervals": [
                {
                    "destination": _jsonable(item.destination),
                    "lower": _fdoc(item.lower),
                    "upper": _fdoc(item.upper),
                }
                for item in self.intervals
            ],
            "reward_lower": _fdoc(self.reward_lower),
            "reward_upper": _fdoc(self.reward_upper),
            "ground_row_ids": list(self.ground_row_ids),
        }


@dataclass(frozen=True, slots=True)
class PartialStatisticalRAPMV1:
    context_id: str
    skeleton_id: str
    profile_id: str
    evidence_id: str
    epoch_index: int
    rows: tuple[PartialRAPMRowV1, ...]
    known_ground_row_count: int
    exact_local_support_rows_used: int
    source_dynamics_imported: bool = False
    complete_closure_imported: bool = False

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "partial model context"),
            (self.skeleton_id, "partial model skeleton"),
            (self.profile_id, "partial model profile"),
            (self.evidence_id, "partial model evidence"),
        ):
            _cid(value, field)
        if (
            self.epoch_index not in (1, 2)
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not PartialRAPMRowV1 for item in self.rows)
            or tuple(repr(item.support_key) for item in self.rows)
            != tuple(sorted({repr(item.support_key) for item in self.rows}))
            or type(self.known_ground_row_count) is not int
            or self.known_ground_row_count <= 0
            or self.exact_local_support_rows_used
            != self.known_ground_row_count
            or self.source_dynamics_imported is not False
            or self.complete_closure_imported is not False
        ):
            raise VariableOrderGraphInvariantViolation(
                "partial statistical RAPM is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_partial_rapm.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "skeleton_id": self.skeleton_id,
            "profile_id": self.profile_id,
            "evidence_id": self.evidence_id,
            "epoch_index": self.epoch_index,
            "rows": [item.to_document() for item in self.rows],
            "known_ground_row_count": self.known_ground_row_count,
            "exact_local_support_rows_used": (
                self.exact_local_support_rows_used
            ),
            "source_dynamics_imported": False,
            "complete_closure_imported": False,
        }

    @property
    def model_id(self) -> str:
        return _content_id("model", self._payload())


def _atom_destination(
    profile: PortableGraphCoordinateProfileV1,
    context: VariableOrderGraphContextV1,
    remaining_horizon: int,
    atom: VariableGraphAtomV1 | ObservedVariableGraphAtomV1,
) -> DestinationKey:
    if atom.failure:
        return ("FAILURE",)
    if remaining_horizon == 1:
        return ("SAFE_TERMINAL",)
    next_ir = _target_state_ir(
        context,
        atom.next_state,
        remaining_horizon - 1,
    )
    return (
        "ACTIVE",
        remaining_horizon - 1,
        _state_coordinate(profile, next_ir),
    )


def build_partial_statistical_rapm_v1(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
    profile: PortableGraphCoordinateProfileV1,
    evidence: SparseVariableGraphEvidenceV1,
    verification: SparseEvidenceVerificationV1,
) -> PartialStatisticalRAPMV1:
    if (
        evidence.context_id != context.context_id
        or verification.context_id != context.context_id
        or verification.evidence_id != evidence.evidence_id
        or profile.skeleton_id != skeleton.skeleton_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "partial RAPM evidence/profile binding is invalid"
        )
    groups: dict[
        str,
        tuple[
            tuple[int, TaggedCoordinate, TaggedCoordinate],
            list[
                tuple[
                    PackedVariableGraphRowV1,
                    dict[DestinationKey, tuple[Fraction, Fraction]],
                    Fraction,
                ]
            ],
        ],
    ] = {}
    for row in evidence.root_rows + evidence.continuation_rows:
        support = _support_key(
            profile,
            context,
            row.catalogue,
            row.action,
        )
        atoms = row.atom_descriptors
        structural_destinations = {
            _atom_destination(
                profile,
                context,
                row.catalogue.remaining_horizon,
                atom,
            )
            for atom in atoms
        }
        counts: dict[DestinationKey, int] = defaultdict(int)
        ordinals_by_destination: dict[
            DestinationKey,
            set[int],
        ] = defaultdict(set)
        for atom in atoms:
            destination = _atom_destination(
                profile,
                context,
                row.catalogue.remaining_horizon,
                atom,
            )
            counts[destination] += row.ordinal_counts[atom.ordinal]
            ordinals_by_destination[destination].add(atom.ordinal)
        bounds = {
            destination: (
                (Fraction(1), Fraction(1))
                if len(ordinals_by_destination[destination])
                == row.atom_count
                else (
                    max(
                        Fraction(0),
                        Fraction(counts[destination], row.sample_count)
                        - HOEFFDING_RADIUS,
                    ),
                    min(
                        Fraction(1),
                        Fraction(counts[destination], row.sample_count)
                        + HOEFFDING_RADIUS,
                    ),
                )
            )
            for destination in structural_destinations
        }
        key = repr(support)
        rewards = {atom.normalized_reward for atom in atoms}
        if len(rewards) != 1:
            raise VariableOrderGraphInvariantViolation(
                "one local support row has nondeterministic immediate reward"
            )
        reward = next(iter(rewards))
        prior = groups.get(key)
        if prior is None:
            groups[key] = (support, [(row, bounds, reward)])
        else:
            if prior[0] != support:
                raise AssertionError("support repr collision")
            prior[1].append((row, bounds, reward))
    model_rows: list[PartialRAPMRowV1] = []
    for key in sorted(groups):
        support, members = groups[key]
        destinations = {
            destination
            for _, bounds, _ in members
            for destination in bounds
        }
        intervals = tuple(
            StatisticalDestinationIntervalV1(
                destination,
                min(
                    bounds.get(destination, (Fraction(0), Fraction(0)))[0]
                    for _, bounds, _ in members
                ),
                max(
                    bounds.get(destination, (Fraction(0), Fraction(0)))[1]
                    for _, bounds, _ in members
                ),
            )
            for destination in sorted(destinations, key=repr)
        )
        model_rows.append(
            PartialRAPMRowV1(
                support,
                intervals,
                min(reward for _, _, reward in members),
                max(reward for _, _, reward in members),
                tuple(sorted(row.row_id for row, _, _ in members)),
            )
        )
    return PartialStatisticalRAPMV1(
        context.context_id,
        skeleton.skeleton_id,
        profile.profile_id,
        evidence.evidence_id,
        1 + profile.refinement_index,
        tuple(model_rows),
        evidence.ground_row_count,
        evidence.ground_row_count,
    )


def _maximize_interval_expectation(
    intervals: tuple[StatisticalDestinationIntervalV1, ...],
    values: Mapping[DestinationKey, Fraction],
) -> Fraction:
    probabilities = {item.destination: item.lower for item in intervals}
    residual = 1 - sum(probabilities.values(), Fraction(0))
    for interval in sorted(
        intervals,
        key=lambda item: (-values[item.destination], repr(item.destination)),
    ):
        addition = min(
            interval.upper - probabilities[interval.destination],
            residual,
        )
        probabilities[interval.destination] += addition
        residual -= addition
        if residual == 0:
            break
    if residual != 0:
        raise VariableOrderGraphInvariantViolation(
            "statistical intervals do not cover one simplex"
        )
    return sum(
        probabilities[destination] * values[destination]
        for destination in probabilities
    )


def _minimize_interval_expectation(
    intervals: tuple[StatisticalDestinationIntervalV1, ...],
    values: Mapping[DestinationKey, Fraction],
) -> Fraction:
    probabilities = {item.destination: item.lower for item in intervals}
    residual = 1 - sum(probabilities.values(), Fraction(0))
    for interval in sorted(
        intervals,
        key=lambda item: (values[item.destination], repr(item.destination)),
    ):
        addition = min(
            interval.upper - probabilities[interval.destination],
            residual,
        )
        probabilities[interval.destination] += addition
        residual -= addition
        if residual == 0:
            break
    if residual != 0:
        raise VariableOrderGraphInvariantViolation(
            "statistical intervals do not cover one simplex"
        )
    return sum(
        probabilities[destination] * values[destination]
        for destination in probabilities
    )


def _registered_query_reward_ceiling(
    context: VariableOrderGraphContextV1,
) -> Fraction:
    root = RelationalGraphMergeKernelV2(context).root_state()
    root_actions = _actions_on_topology(context.topology, root)
    root_rank = max(root.ranks[item[0]] for item in root_actions)
    first = (
        Fraction(2 ** (root_rank + 1), 2 ** (RANK_CAP + 1))
        / REWARD_NORMALIZER
    )
    maximum_next_rank = max(
        max(root.ranks),
        min(root_rank + 1, RANK_CAP),
        LOW_RANK + 1,
    )
    second = (
        Fraction(
            2 ** (maximum_next_rank + 1),
            2 ** (RANK_CAP + 1),
        )
        / REWARD_NORMALIZER
    )
    return first + second


class PortableGraphAuditOutcome(str, Enum):
    CONDITIONALLY_CERTIFIED = (
        "CONDITIONALLY_CERTIFIED_REGISTERED_PRNG_IID"
    )
    FAILED_RISK_OR_ALIAS = "FAILED_RISK_OR_ALIAS"


@dataclass(frozen=True, slots=True)
class GroundConcretizerEntryV1:
    state_id: str
    distinct_ground_actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "concretizer state")
        if (
            type(self.distinct_ground_actions) is not tuple
            or not self.distinct_ground_actions
            or self.distinct_ground_actions
            != tuple(sorted(set(self.distinct_ground_actions)))
        ):
            raise VariableOrderGraphInvariantViolation(
                "fixed distinct-action concretizer entry is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "distinct_ground_actions": [
                list(item) for item in self.distinct_ground_actions
            ],
            "distribution": "UNIFORM_OVER_DISTINCT_GROUND_ACTIONS",
        }


@dataclass(frozen=True, slots=True)
class AbstractPolicyAssignmentV1:
    remaining_horizon: int
    state_coordinate: TaggedCoordinate
    semantic_action_coordinate: TaggedCoordinate
    concretizer_entries: tuple[GroundConcretizerEntryV1, ...]

    def __post_init__(self) -> None:
        if (
            self.remaining_horizon not in (1, HORIZON)
            or type(self.state_coordinate) is not tuple
            or not self.state_coordinate
            or type(self.semantic_action_coordinate) is not tuple
            or not self.semantic_action_coordinate
            or type(self.concretizer_entries) is not tuple
            or not self.concretizer_entries
            or any(
                type(item) is not GroundConcretizerEntryV1
                for item in self.concretizer_entries
            )
            or tuple(item.state_id for item in self.concretizer_entries)
            != tuple(
                sorted(
                    {item.state_id for item in self.concretizer_entries}
                )
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "abstract policy assignment is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "remaining_horizon": self.remaining_horizon,
            "state_coordinate": _jsonable(self.state_coordinate),
            "semantic_action_coordinate": _jsonable(
                self.semantic_action_coordinate
            ),
            "concretizer_entries": [
                item.to_document() for item in self.concretizer_entries
            ],
        }


@dataclass(frozen=True, slots=True)
class PortableGraphAuditV1:
    context_id: str
    model_id: str
    profile_id: str
    outcome: PortableGraphAuditOutcome
    failure_upper: Fraction
    normalized_reward_lower: Fraction
    normalized_regret_upper: Fraction
    selected_root_action_coordinate: TaggedCoordinate
    policy_assignments: tuple[AbstractPolicyAssignmentV1, ...]
    decision_count: int
    generative_draws_charged: int
    exact_local_support_rows_charged: int
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE

    @property
    def policy_id(self) -> str:
        return _content_id(
            "policy",
            {
                "schema": "acfqp.variable_order_graph_abstract_policy.v1",
                "schema_version": SCHEMA_VERSION,
                "context_id": self.context_id,
                "profile_id": self.profile_id,
                "policy_assignments": [
                    item.to_document() for item in self.policy_assignments
                ],
                "concretizer": (
                    "UNIFORM_OVER_DISTINCT_MATCHING_GROUND_ACTIONS"
                ),
            },
        )

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "graph audit context"),
            (self.model_id, "graph audit model"),
            (self.profile_id, "graph audit profile"),
        ):
            _cid(value, field)
        if (
            type(self.outcome) is not PortableGraphAuditOutcome
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or type(self.normalized_reward_lower) is not Fraction
            or not 0 <= self.normalized_reward_lower <= 1
            or type(self.normalized_regret_upper) is not Fraction
            or not 0 <= self.normalized_regret_upper <= 1
            or type(self.selected_root_action_coordinate) is not tuple
            or not self.selected_root_action_coordinate
            or type(self.policy_assignments) is not tuple
            or not self.policy_assignments
            or any(
                type(item) is not AbstractPolicyAssignmentV1
                for item in self.policy_assignments
            )
            or sum(
                item.remaining_horizon == HORIZON
                for item in self.policy_assignments
            )
            != 1
            or next(
                item.semantic_action_coordinate
                for item in self.policy_assignments
                if item.remaining_horizon == HORIZON
            )
            != self.selected_root_action_coordinate
            or type(self.decision_count) is not int
            or self.decision_count != len(self.policy_assignments)
            or type(self.generative_draws_charged) is not int
            or self.generative_draws_charged <= 0
            or type(self.exact_local_support_rows_charged) is not int
            or self.exact_local_support_rows_charged <= 0
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
        ):
            raise VariableOrderGraphInvariantViolation(
                "portable graph audit is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_audit.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "model_id": self.model_id,
            "profile_id": self.profile_id,
            "outcome": self.outcome.value,
            "failure_upper": _fdoc(self.failure_upper),
            "normalized_reward_lower": _fdoc(self.normalized_reward_lower),
            "normalized_regret_upper": _fdoc(self.normalized_regret_upper),
            "selected_root_action_coordinate": _jsonable(
                self.selected_root_action_coordinate
            ),
            "policy_assignments": [
                item.to_document() for item in self.policy_assignments
            ],
            "policy_id": self.policy_id,
            "decision_count": self.decision_count,
            "generative_draws_charged": self.generative_draws_charged,
            "exact_local_support_rows_charged": (
                self.exact_local_support_rows_charged
            ),
            "statistical_claim_scope": self.statistical_claim_scope,
        }

    @property
    def audit_id(self) -> str:
        return _content_id("audit", self._payload())


def audit_partial_statistical_rapm_v1(
    context: VariableOrderGraphContextV1,
    profile: PortableGraphCoordinateProfileV1,
    model: PartialStatisticalRAPMV1,
    evidence: SparseVariableGraphEvidenceV1,
) -> PortableGraphAuditV1:
    if (
        model.context_id != context.context_id
        or model.profile_id != profile.profile_id
        or model.evidence_id != evidence.evidence_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "partial model audit binding is invalid"
        )
    model_rows = {item.support_key: item for item in model.rows}
    members: dict[
        tuple[int, TaggedCoordinate],
        list[VariableGraphCatalogueV1],
    ] = defaultdict(list)
    root_catalogue = evidence.root_rows[0].catalogue
    catalogues = (root_catalogue,) + evidence.continuation_catalogues
    for catalogue in catalogues:
        state_ir = _profile_state_ir(context, catalogue)
        members[
            (
                catalogue.remaining_horizon,
                _state_coordinate(profile, state_ir),
            )
        ].append(catalogue)
    action_coordinates: dict[
        tuple[int, TaggedCoordinate],
        tuple[TaggedCoordinate, ...],
    ] = {}
    for state_key, state_members in members.items():
        sets: list[set[TaggedCoordinate]] = []
        for catalogue in state_members:
            state_ir = _profile_state_ir(context, catalogue)
            sets.append(
                {
                    _action_coordinate(
                        profile,
                        state_ir,
                        _profile_action_slot(state_ir, action),
                    )
                    for action in catalogue.actions
                }
            )
        common = set.intersection(*sets)
        if not common:
            # An unavailable abstract action is conservatively direct bad.
            action_coordinates[state_key] = ()
        else:
            action_coordinates[state_key] = tuple(sorted(common, key=repr))
    decisions: dict[
        tuple[int, TaggedCoordinate],
        tuple[Fraction, Fraction],
    ] = {}
    selected_coordinates: dict[
        tuple[int, TaggedCoordinate],
        TaggedCoordinate,
    ] = {}
    for state_key in sorted(
        (item for item in members if item[0] == 1),
        key=repr,
    ):
        candidates: list[tuple[Fraction, Fraction, TaggedCoordinate]] = []
        for action_coordinate in action_coordinates[state_key]:
            support = (1, state_key[1], action_coordinate)
            row = model_rows.get(support)
            if row is None:
                candidates.append(
                    (Fraction(1), Fraction(0), action_coordinate)
                )
                continue
            risk_values = {
                interval.destination: (
                    Fraction(1)
                    if interval.destination[0] == "FAILURE"
                    else Fraction(0)
                )
                for interval in row.intervals
            }
            candidates.append(
                (
                    _maximize_interval_expectation(
                        row.intervals,
                        risk_values,
                    ),
                    row.reward_lower,
                    action_coordinate,
                )
            )
        if candidates:
            risk, reward, selected_coordinate = min(
                candidates,
                key=lambda item: (item[0], -item[1], repr(item[2])),
            )
            decisions[state_key] = (risk, reward)
            selected_coordinates[state_key] = selected_coordinate
        else:
            decisions[state_key] = (Fraction(1), Fraction(0))
    root_state_key = next(
        item for item in members if item[0] == HORIZON
    )
    root_candidates: list[
        tuple[Fraction, Fraction, TaggedCoordinate]
    ] = []
    for action_coordinate in action_coordinates[root_state_key]:
        support = (HORIZON, root_state_key[1], action_coordinate)
        row = model_rows.get(support)
        if row is None:
            root_candidates.append(
                (Fraction(1), Fraction(0), action_coordinate)
            )
            continue
        risk_values: dict[DestinationKey, Fraction] = {}
        reward_values: dict[DestinationKey, Fraction] = {}
        for interval in row.intervals:
            destination = interval.destination
            if destination[0] == "FAILURE":
                risk_values[destination] = Fraction(1)
                reward_values[destination] = Fraction(0)
            elif destination[0] == "SAFE_TERMINAL":
                risk_values[destination] = Fraction(0)
                reward_values[destination] = Fraction(0)
            else:
                decision = decisions.get(
                    (destination[1], destination[2]),
                    (Fraction(1), Fraction(0)),
                )
                risk_values[destination] = decision[0]
                reward_values[destination] = decision[1]
        root_candidates.append(
            (
                _maximize_interval_expectation(
                    row.intervals,
                    risk_values,
                ),
                row.reward_lower
                + _minimize_interval_expectation(
                    row.intervals,
                    reward_values,
                ),
                action_coordinate,
            )
        )
    feasible = tuple(
        item
        for item in root_candidates
        if item[0] < context.risk_tolerance
    )
    if feasible:
        failure_upper, reward_lower, selected_action = min(
            feasible,
            key=lambda item: (-item[1], item[0], repr(item[2])),
        )
    else:
        failure_upper, reward_lower, selected_action = min(
            root_candidates,
            key=lambda item: (item[0], -item[1], repr(item[2])),
        )
    normalized_regret_upper = max(
        Fraction(0),
        _registered_query_reward_ceiling(context) - reward_lower,
    )
    selected_coordinates[root_state_key] = selected_action
    assignments: list[AbstractPolicyAssignmentV1] = []
    for state_key, action_coordinate in sorted(
        selected_coordinates.items(),
        key=lambda item: (-item[0][0], repr(item[0][1])),
    ):
        concretizer_entries: list[GroundConcretizerEntryV1] = []
        for catalogue in members[state_key]:
            state_ir = _profile_state_ir(context, catalogue)
            matching = tuple(
                sorted(
                    action
                    for action in catalogue.actions
                    if _action_coordinate(
                        profile,
                        state_ir,
                        _profile_action_slot(state_ir, action),
                    )
                    == action_coordinate
                )
            )
            if not matching:
                raise VariableOrderGraphInvariantViolation(
                    "selected semantic action has empty ground support"
                )
            concretizer_entries.append(
                GroundConcretizerEntryV1(
                    catalogue.state.state_id,
                    matching,
                )
            )
        assignments.append(
            AbstractPolicyAssignmentV1(
                state_key[0],
                state_key[1],
                action_coordinate,
                tuple(
                    sorted(
                        concretizer_entries,
                        key=lambda item: item.state_id,
                    )
                ),
            )
        )
    outcome = (
        PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        if (
            failure_upper < context.risk_tolerance
            and normalized_regret_upper <= Fraction(1, 20)
        )
        else PortableGraphAuditOutcome.FAILED_RISK_OR_ALIAS
    )
    return PortableGraphAuditV1(
        context.context_id,
        model.model_id,
        profile.profile_id,
        outcome,
        failure_upper,
        reward_lower,
        normalized_regret_upper,
        selected_action,
        tuple(assignments),
        len(assignments),
        evidence.generative_draw_count,
        evidence.exact_local_support_row_count,
    )


@dataclass(frozen=True, slots=True)
class GraphRefinementCandidateV1:
    state_extra: PortableRelationalProgramV1 | None
    action_extra: PortableRelationalProgramV1 | None
    profile_id: str
    model_id: str
    audit_id: str
    outcome: PortableGraphAuditOutcome
    failure_upper: Fraction
    abstract_support_count: int
    added_node_count: int

    def __post_init__(self) -> None:
        for value, field in (
            (self.profile_id, "refinement candidate profile"),
            (self.model_id, "refinement candidate model"),
            (self.audit_id, "refinement candidate audit"),
        ):
            _cid(value, field)
        if (
            self.state_extra is None
            and self.action_extra is None
            or (
                self.state_extra is not None
                and (
                    type(self.state_extra) is not PortableRelationalProgramV1
                    or self.state_extra.context
                    is not RelationalProgramContext.STATE
                )
            )
            or (
                self.action_extra is not None
                and (
                    type(self.action_extra) is not PortableRelationalProgramV1
                    or self.action_extra.context
                    is not RelationalProgramContext.STATE_ACTION
                )
            )
            or type(self.outcome) is not PortableGraphAuditOutcome
            or type(self.failure_upper) is not Fraction
            or not 0 <= self.failure_upper <= 1
            or type(self.abstract_support_count) is not int
            or self.abstract_support_count <= 0
            or type(self.added_node_count) is not int
            or self.added_node_count <= 0
        ):
            raise VariableOrderGraphInvariantViolation(
                "graph refinement candidate is invalid"
            )

    def to_document(self) -> dict[str, Any]:
        return {
            "state_extra": (
                None
                if self.state_extra is None
                else self.state_extra.to_document()
            ),
            "action_extra": (
                None
                if self.action_extra is None
                else self.action_extra.to_document()
            ),
            "profile_id": self.profile_id,
            "model_id": self.model_id,
            "audit_id": self.audit_id,
            "outcome": self.outcome.value,
            "failure_upper": _fdoc(self.failure_upper),
            "abstract_support_count": self.abstract_support_count,
            "added_node_count": self.added_node_count,
        }


@dataclass(frozen=True, slots=True)
class TargetGraphProgramTraceV1:
    context_id: str
    failed_audit_id: str
    generation: TargetRelationalProgramGenerationV1
    candidates: tuple[GraphRefinementCandidateV1, ...]
    selected_profile_id: str | None
    selected_program_rendered: str | None
    sound_cover_found: bool
    best_failure_upper: Fraction

    def __post_init__(self) -> None:
        _cid(self.context_id, "program trace context")
        _cid(self.failed_audit_id, "program trace failed audit")
        if (
            type(self.generation) is not TargetRelationalProgramGenerationV1
            or type(self.candidates) is not tuple
            or not self.candidates
            or any(
                type(item) is not GraphRefinementCandidateV1
                for item in self.candidates
            )
            or tuple(item.profile_id for item in self.candidates)
            != tuple(sorted({item.profile_id for item in self.candidates}))
            or type(self.sound_cover_found) is not bool
            or type(self.best_failure_upper) is not Fraction
            or self.best_failure_upper
            != min(item.failure_upper for item in self.candidates)
            or (
                self.sound_cover_found
                != (self.selected_profile_id is not None)
            )
            or (
                self.sound_cover_found
                != (self.selected_program_rendered is not None)
            )
            or (
                self.selected_profile_id is not None
                and self.selected_profile_id
                not in {item.profile_id for item in self.candidates}
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "target graph program trace is invalid"
            )
        if self.selected_profile_id is not None:
            _cid(self.selected_profile_id, "program trace selected profile")

    @property
    def candidate_count(self) -> int:
        return len(self.candidates)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_program_trace.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "failed_audit_id": self.failed_audit_id,
            "generation_id": self.generation.generation_id,
            "target_program_generation_count": (
                self.generation.target_program_generation_count
            ),
            "semantic_program_count": len(self.generation.registry.programs),
            "semantic_program_count_by_depth": list(
                self.generation.registry.semantic_program_count_by_depth
            ),
            "source_registry_access_count": 0,
            "source_candidate_metric_access_count": 0,
            "primitive_invention_count": 0,
            "candidates": [item.to_document() for item in self.candidates],
            "candidate_count": self.candidate_count,
            "selected_profile_id": self.selected_profile_id,
            "selected_program_rendered": self.selected_program_rendered,
            "sound_cover_found": self.sound_cover_found,
            "best_failure_upper": _fdoc(self.best_failure_upper),
        }

    @property
    def trace_id(self) -> str:
        return _content_id("generation", self._payload())


def _fresh_refinement_programs(
    skeleton: PortableRelationalSkeletonV1,
    generation: TargetRelationalProgramGenerationV1,
) -> tuple[
    tuple[PortableRelationalProgramV1, ...],
    tuple[PortableRelationalProgramV1, ...],
]:
    state_extras = tuple(
        item
        for item in generation.registry.programs
        if item.context is RelationalProgramContext.STATE
        and item.result_type
        in (RelationalProgramType.INTEGER, RelationalProgramType.SIGNATURE)
        and item.program_id != skeleton.state_program.program_id
    )
    action_extras = tuple(
        item
        for item in generation.registry.programs
        if item.context is RelationalProgramContext.STATE_ACTION
        and item.result_type is RelationalProgramType.INTEGER
        and item.program_id != skeleton.action_program.program_id
    )
    return state_extras, action_extras


def generate_and_test_target_graph_programs_v1(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
    base_profile: PortableGraphCoordinateProfileV1,
    base_model: PartialStatisticalRAPMV1,
    base_audit: PortableGraphAuditV1,
    evidence: SparseVariableGraphEvidenceV1,
    verification: SparseEvidenceVerificationV1,
) -> tuple[
    TargetGraphProgramTraceV1,
    PortableGraphCoordinateProfileV1 | None,
    PartialStatisticalRAPMV1 | None,
    PortableGraphAuditV1 | None,
]:
    if (
        base_audit.outcome
        is not PortableGraphAuditOutcome.FAILED_RISK_OR_ALIAS
        or base_audit.model_id != base_model.model_id
        or base_profile.profile_id != base_model.profile_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "target program generation requires a current failed base proof"
        )
    target_log = target_relational_observation_log_v1(context, evidence)
    failed_proof = FailedRelationalProofRefV1(
        context.context_id,
        base_model.model_id,
        base_audit.audit_id,
        "ALIAS_WIDTH",
    )
    generation = generate_target_relational_programs_v1(
        skeleton,
        failed_proof,
        target_log,
    )
    state_extras, action_extras = _fresh_refinement_programs(
        skeleton,
        generation,
    )
    candidate_inputs: list[
        tuple[
            PortableRelationalProgramV1 | None,
            PortableRelationalProgramV1 | None,
        ]
    ] = (
        [(item, None) for item in state_extras]
        + [(None, item) for item in action_extras]
        + [
            (state_extra, action_extra)
            for state_extra in state_extras
            for action_extra in action_extras
        ]
    )
    evaluated: list[
        tuple[
            GraphRefinementCandidateV1,
            PortableGraphCoordinateProfileV1,
            PartialStatisticalRAPMV1,
            PortableGraphAuditV1,
        ]
    ] = []
    for state_extra, action_extra in candidate_inputs:
        profile = PortableGraphCoordinateProfileV1(
            skeleton.skeleton_id,
            (skeleton.state_program,)
            + (() if state_extra is None else (state_extra,)),
            (skeleton.action_program,)
            + (() if action_extra is None else (action_extra,)),
            1,
            generation.generation_id,
            base_audit.audit_id,
        )
        model = build_partial_statistical_rapm_v1(
            context,
            skeleton,
            profile,
            evidence,
            verification,
        )
        audit = audit_partial_statistical_rapm_v1(
            context,
            profile,
            model,
            evidence,
        )
        node_count = (
            0 if state_extra is None else state_extra.node_count
        ) + (0 if action_extra is None else action_extra.node_count)
        evaluated.append(
            (
                GraphRefinementCandidateV1(
                    state_extra,
                    action_extra,
                    profile.profile_id,
                    model.model_id,
                    audit.audit_id,
                    audit.outcome,
                    audit.failure_upper,
                    len(model.rows),
                    node_count,
                ),
                profile,
                model,
                audit,
            )
        )
    certified = tuple(
        item
        for item in evaluated
        if item[3].outcome
        is PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
    )
    selected = (
        None
        if not certified
        else min(
            certified,
            key=lambda item: (
                item[0].added_node_count,
                item[0].abstract_support_count,
                item[0].profile_id,
            ),
        )
    )
    summaries = tuple(
        sorted((item[0] for item in evaluated), key=lambda item: item.profile_id)
    )
    selected_rendered = None
    if selected is not None:
        extras = tuple(
            item
            for item in (
                selected[0].state_extra,
                selected[0].action_extra,
            )
            if item is not None
        )
        selected_rendered = " + ".join(item.rendered for item in extras)
    trace = TargetGraphProgramTraceV1(
        context.context_id,
        base_audit.audit_id,
        generation,
        summaries,
        None if selected is None else selected[1].profile_id,
        selected_rendered,
        selected is not None,
        min(item.failure_upper for item in summaries),
    )
    if selected is None:
        return trace, None, None, None
    return trace, selected[1], selected[2], selected[3]


@dataclass(frozen=True, slots=True)
class SparseCoverageCertificateV1:
    context_id: str
    evidence_id: str
    acquired_ground_rows: int
    matched_h2_ground_rows: int
    explicitly_unknown_ground_rows: int
    acquired_fraction: Fraction
    operational_complete_closure_calls: int = 0

    def __post_init__(self) -> None:
        _cid(self.context_id, "coverage context")
        _cid(self.evidence_id, "coverage evidence")
        if (
            type(self.acquired_ground_rows) is not int
            or self.acquired_ground_rows <= 0
            or type(self.matched_h2_ground_rows) is not int
            or self.matched_h2_ground_rows < self.acquired_ground_rows
            or self.explicitly_unknown_ground_rows
            != self.matched_h2_ground_rows - self.acquired_ground_rows
            or self.acquired_fraction
            != Fraction(
                self.acquired_ground_rows,
                self.matched_h2_ground_rows,
            )
            or self.operational_complete_closure_calls != 0
        ):
            raise VariableOrderGraphInvariantViolation(
                "sparse coverage certificate is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_sparse_coverage.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "evidence_id": self.evidence_id,
            "acquired_ground_rows": self.acquired_ground_rows,
            "matched_h2_ground_rows": self.matched_h2_ground_rows,
            "explicitly_unknown_ground_rows": (
                self.explicitly_unknown_ground_rows
            ),
            "acquired_fraction": _fdoc(self.acquired_fraction),
            "operational_complete_closure_calls": 0,
        }

    @property
    def coverage_id(self) -> str:
        return _content_id("coverage", self._payload())


@dataclass(frozen=True, slots=True)
class VariableGraphMatchedEvaluationV1:
    context_id: str
    result_id: str
    matched_direct_control: VariableGraphColdControlV1
    coverage: SparseCoverageCertificateV1
    lifted_policy_id: str
    lifted_exact_failure_probability: Fraction
    lifted_exact_normalized_reward: Fraction
    audit_bounds_cover_exact_lift: bool
    exact_regret_check_passed: bool
    expected_fixture_role_passed: bool
    evaluation_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        _cid(self.context_id, "matched evaluation context")
        _cid(self.result_id, "matched evaluation result")
        if (
            type(self.matched_direct_control)
            is not VariableGraphColdControlV1
            or self.matched_direct_control.context_id != self.context_id
            or type(self.coverage) is not SparseCoverageCertificateV1
            or self.coverage.context_id != self.context_id
            or _cid(self.lifted_policy_id, "matched evaluation policy")
            != self.lifted_policy_id
            or type(self.lifted_exact_failure_probability) is not Fraction
            or not 0 <= self.lifted_exact_failure_probability <= 1
            or type(self.lifted_exact_normalized_reward) is not Fraction
            or not 0 <= self.lifted_exact_normalized_reward <= 1
            or self.audit_bounds_cover_exact_lift is not True
            or self.exact_regret_check_passed is not True
            or self.expected_fixture_role_passed is not True
            or self.evaluation_lane != "EVALUATION_ONLY"
        ):
            raise VariableOrderGraphInvariantViolation(
                "matched direct evaluation is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_matched_evaluation.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "result_id": self.result_id,
            "matched_direct_control_id": (
                self.matched_direct_control.control_id
            ),
            "coverage_id": self.coverage.coverage_id,
            "lifted_policy_id": self.lifted_policy_id,
            "lifted_exact_failure_probability": _fdoc(
                self.lifted_exact_failure_probability
            ),
            "lifted_exact_normalized_reward": _fdoc(
                self.lifted_exact_normalized_reward
            ),
            "audit_bounds_cover_exact_lift": True,
            "exact_regret_check_passed": True,
            "expected_fixture_role_passed": True,
            "evaluation_lane": self.evaluation_lane,
        }

    @property
    def evaluation_id(self) -> str:
        return _content_id("evaluation", self._payload())


def _evaluate_exact_abstract_policy_lift(
    result: "VariableGraphContextResultV1",
) -> tuple[Fraction, Fraction]:
    context = result.context
    profile = result.final_profile
    kernel = RelationalGraphMergeKernelV2(context)
    assignments = {
        (item.remaining_horizon, item.state_coordinate): item
        for item in result.final_audit.policy_assignments
    }
    memo: dict[
        tuple[str, int],
        tuple[Fraction, Fraction],
    ] = {}

    def solve(
        state: VariableGraphStateV1,
        remaining: int,
    ) -> tuple[Fraction, Fraction]:
        key = (state.state_id, remaining)
        if key in memo:
            return memo[key]
        state_ir = _target_state_ir(context, state, remaining)
        state_coordinate = _state_coordinate(profile, state_ir)
        assignment = assignments.get((remaining, state_coordinate))
        if assignment is None:
            raise VariableOrderGraphInvariantViolation(
                "exact lift lacks a reachable abstract assignment"
            )
        entry = next(
            (
                item
                for item in assignment.concretizer_entries
                if item.state_id == state.state_id
            ),
            None,
        )
        if entry is None:
            raise VariableOrderGraphInvariantViolation(
                "exact lift lacks a reachable ground concretizer"
            )
        action_weight = Fraction(1, len(entry.distinct_ground_actions))
        risk = Fraction(0)
        reward = Fraction(0)
        for action in entry.distinct_ground_actions:
            atoms = kernel.atoms(state, action)
            immediate = atoms[0].normalized_reward
            action_risk = Fraction(0)
            action_future_reward = Fraction(0)
            for atom in atoms:
                if atom.failure:
                    action_risk += atom.probability
                elif remaining > 1:
                    child_risk, child_reward = solve(
                        atom.next_state,
                        remaining - 1,
                    )
                    action_risk += atom.probability * child_risk
                    action_future_reward += atom.probability * child_reward
            risk += action_weight * action_risk
            reward += action_weight * (immediate + action_future_reward)
        memo[key] = (risk, reward)
        return risk, reward

    return solve(kernel.root_state(), HORIZON)


def evaluate_variable_graph_context_v1(
    result: "VariableGraphContextResultV1",
) -> VariableGraphMatchedEvaluationV1:
    if type(result) is not VariableGraphContextResultV1:
        raise VariableOrderGraphInvariantViolation(
            "matched evaluation requires an exact operational result"
        )
    cold = cold_variable_graph_control_v1(result.context)
    coverage = SparseCoverageCertificateV1(
        result.context.context_id,
        result.evidence.evidence_id,
        result.evidence.ground_row_count,
        cold.matched_h2_row_count,
        cold.matched_h2_row_count - result.evidence.ground_row_count,
        Fraction(
            result.evidence.ground_row_count,
            cold.matched_h2_row_count,
        ),
    )
    expected_risk = (
        Fraction(99, 5000)
        if registered_graph_target_role_v1(result.context)
        is GraphTargetRole.POSITIVE
        else Fraction(2277, 16000)
    )
    lift_risk, lift_reward = _evaluate_exact_abstract_policy_lift(result)
    audit_bounds_cover = (
        lift_risk <= result.final_audit.failure_upper
        and lift_reward >= result.final_audit.normalized_reward_lower
    )
    regret_check = (
        cold.selected_exact_reward - lift_reward
        <= result.final_audit.normalized_regret_upper
    )
    role_passed = (
        cold.exact_root_failure_probability == expected_risk
        and cold.selected_exact_reward == Fraction(3, 64)
        and (
            (
                registered_graph_target_role_v1(result.context)
                is GraphTargetRole.POSITIVE
                and not result.fallback_used
                and lift_risk < result.context.risk_tolerance
            )
            or (
                registered_graph_target_role_v1(result.context)
                is GraphTargetRole.NO_SOUND_COVER
                and result.fallback_used
                and result.fallback_proof is not None
                and result.fallback_proof.exact_failure_probability
                == cold.exact_root_failure_probability
                and result.fallback_proof.exact_normalized_reward
                == cold.selected_exact_reward
            )
        )
    )
    return VariableGraphMatchedEvaluationV1(
        result.context.context_id,
        result.result_id,
        cold,
        coverage,
        result.final_audit.policy_id,
        lift_risk,
        lift_reward,
        audit_bounds_cover,
        regret_check,
        role_passed,
    )


class VariableGraphTerminalOutcome(str, Enum):
    CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE = (
        "CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE"
    )
    FULL_GROUND_FALLBACK_PLAN_CERTIFICATE = (
        "FULL_GROUND_FALLBACK_PLAN_CERTIFICATE"
    )


@dataclass(frozen=True, slots=True)
class VariableGraphContextResultV1:
    context: VariableOrderGraphContextV1
    evidence: SparseVariableGraphEvidenceV1
    verification: SparseEvidenceVerificationV1
    base_profile: PortableGraphCoordinateProfileV1
    base_model: PartialStatisticalRAPMV1
    base_audit: PortableGraphAuditV1
    program_trace: TargetGraphProgramTraceV1 | None
    final_profile: PortableGraphCoordinateProfileV1
    final_model: PartialStatisticalRAPMV1
    final_audit: PortableGraphAuditV1
    fallback_proof: ExactGroundFallbackProofV1 | None
    terminal_outcome: VariableGraphTerminalOutcome
    fallback_used: bool
    false_certificate_count: int = 0

    def __post_init__(self) -> None:
        objects = (
            (self.context, VariableOrderGraphContextV1),
            (self.evidence, SparseVariableGraphEvidenceV1),
            (self.verification, SparseEvidenceVerificationV1),
            (self.base_profile, PortableGraphCoordinateProfileV1),
            (self.base_model, PartialStatisticalRAPMV1),
            (self.base_audit, PortableGraphAuditV1),
            (self.final_profile, PortableGraphCoordinateProfileV1),
            (self.final_model, PartialStatisticalRAPMV1),
            (self.final_audit, PortableGraphAuditV1),
        )
        if (
            any(type(value) is not expected for value, expected in objects)
            or self.evidence.context_id != self.context.context_id
            or self.final_audit.model_id != self.final_model.model_id
            or type(self.terminal_outcome) is not VariableGraphTerminalOutcome
            or type(self.fallback_used) is not bool
            or self.false_certificate_count != 0
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable graph context result is invalid"
            )
        if (
            self.final_audit.outcome
            is PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        ):
            if (
                self.terminal_outcome
                is not VariableGraphTerminalOutcome.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
                or self.fallback_used
                or self.fallback_proof is not None
                or self.final_audit.failure_upper
                >= self.context.risk_tolerance
            ):
                raise VariableOrderGraphInvariantViolation(
                    "conditional sparse plan certificate is invalid"
                )
        else:
            if (
                self.terminal_outcome
                is not VariableGraphTerminalOutcome.FULL_GROUND_FALLBACK_PLAN_CERTIFICATE
                or not self.fallback_used
                or type(self.fallback_proof)
                is not ExactGroundFallbackProofV1
                or self.fallback_proof.context_id
                != self.context.context_id
                or self.fallback_proof.failed_audit_id
                != self.final_audit.audit_id
                or self.fallback_proof.exact_failure_probability
                >= self.context.risk_tolerance
                or self.program_trace is None
                or self.program_trace.sound_cover_found
            ):
                raise VariableOrderGraphInvariantViolation(
                    "failed abstract proof lacks a valid exact fallback"
                )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_result.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context.context_id,
            "evidence_id": self.evidence.evidence_id,
            "verification_id": self.verification.verification_id,
            "base_profile_id": self.base_profile.profile_id,
            "base_model_id": self.base_model.model_id,
            "base_audit_id": self.base_audit.audit_id,
            "program_trace_id": (
                None if self.program_trace is None else self.program_trace.trace_id
            ),
            "final_profile_id": self.final_profile.profile_id,
            "final_model_id": self.final_model.model_id,
            "final_audit_id": self.final_audit.audit_id,
            "final_policy_id": self.final_audit.policy_id,
            "fallback_proof_id": (
                None
                if self.fallback_proof is None
                else self.fallback_proof.proof_id
            ),
            "terminal_outcome": self.terminal_outcome.value,
            "fallback_used": self.fallback_used,
            "false_certificate_count": 0,
        }

    @property
    def result_id(self) -> str:
        return _content_id("result", self._payload())


@functools.lru_cache(maxsize=3)
def run_variable_graph_context_v1(
    context: VariableOrderGraphContextV1,
    skeleton: PortableRelationalSkeletonV1,
) -> VariableGraphContextResultV1:
    evidence = acquire_sparse_variable_graph_evidence_v1(context, skeleton)
    verification = verify_sparse_variable_graph_evidence_v1(
        context,
        skeleton,
        evidence,
    )
    base_profile = _base_coordinate_profile(skeleton)
    base_model = build_partial_statistical_rapm_v1(
        context,
        skeleton,
        base_profile,
        evidence,
        verification,
    )
    base_audit = audit_partial_statistical_rapm_v1(
        context,
        base_profile,
        base_model,
        evidence,
    )
    trace: TargetGraphProgramTraceV1 | None = None
    final_profile = base_profile
    final_model = base_model
    final_audit = base_audit
    if base_audit.outcome is PortableGraphAuditOutcome.FAILED_RISK_OR_ALIAS:
        trace, proposed_profile, proposed_model, proposed_audit = (
            generate_and_test_target_graph_programs_v1(
                context,
                skeleton,
                base_profile,
                base_model,
                base_audit,
                evidence,
                verification,
            )
        )
        if proposed_profile is not None:
            final_profile = proposed_profile
            final_model = proposed_model
            final_audit = proposed_audit
    fallback = (
        None
        if final_audit.outcome
        is PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        else execute_exact_ground_fallback_v1(context, final_audit)
    )
    return VariableGraphContextResultV1(
        context,
        evidence,
        verification,
        base_profile,
        base_model,
        base_audit,
        trace,
        final_profile,
        final_model,
        final_audit,
        fallback,
        (
            VariableGraphTerminalOutcome.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
            if fallback is None
            else VariableGraphTerminalOutcome.FULL_GROUND_FALLBACK_PLAN_CERTIFICATE
        ),
        fallback is not None,
    )


def _actions_on_topology(
    topology: GraphTopologyV1,
    state: VariableGraphStateV1,
) -> tuple[tuple[int, int, int], ...]:
    if len(state.ranks) != topology.vertex_count or state.failure:
        return ()
    return tuple(
        (first, second, survivor)
        for first, second in topology.edges
        if state.ranks[first] > 0
        and state.ranks[first] == state.ranks[second]
        for survivor in (first, second)
    )


def _atoms_on_topology(
    topology: GraphTopologyV1,
    state: VariableGraphStateV1,
    action: tuple[int, int, int],
) -> tuple[VariableGraphAtomV1, ...]:
    if action not in _actions_on_topology(topology, state):
        raise VariableOrderGraphInvariantViolation(
            "permutation control received an illegal action"
        )
    first, second, survivor = action
    rank = state.ranks[first]
    board = list(state.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, RANK_CAP)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    reward = (
        Fraction(2 ** (rank + 1), 2 ** (RANK_CAP + 1))
        / REWARD_NORMALIZER
    )
    result: list[VariableGraphAtomV1] = []
    for cell in empty:
        for spawn_rank, rank_probability in (
            (LOW_RANK, LOW_RANK_PROBABILITY),
            (LOW_RANK + 1, 1 - LOW_RANK_PROBABILITY),
        ):
            successor = board.copy()
            successor[cell] = spawn_rank
            provisional = VariableGraphStateV1(tuple(successor))
            failure = not _actions_on_topology(topology, provisional)
            result.append(
                VariableGraphAtomV1(
                    len(result),
                    VariableGraphStateV1(tuple(successor), failure),
                    Fraction(1, len(empty)) * rank_probability,
                    reward,
                    failure,
                )
            )
    return tuple(result)


def _minimum_failure_probability_on_topology(
    topology: GraphTopologyV1,
    state: VariableGraphStateV1,
    remaining_horizon: int,
    memo: dict[tuple[VariableGraphStateV1, int], Fraction],
) -> Fraction:
    key = (state, remaining_horizon)
    if key in memo:
        return memo[key]
    if state.failure:
        return Fraction(1)
    if remaining_horizon == 0:
        return Fraction(0)
    actions = _actions_on_topology(topology, state)
    if not actions:
        return Fraction(1)
    values = []
    for action in actions:
        value = Fraction(0)
        for atom in _atoms_on_topology(topology, state, action):
            value += atom.probability * (
                Fraction(1)
                if atom.failure
                else _minimum_failure_probability_on_topology(
                    topology,
                    atom.next_state,
                    remaining_horizon - 1,
                    memo,
                )
            )
        values.append(value)
    result = min(values)
    memo[key] = result
    return result


def _permuted_topology(
    topology: GraphTopologyV1,
    permutation: tuple[int, ...],
) -> GraphTopologyV1:
    return GraphTopologyV1(
        topology.vertex_count,
        _graph_edges(
            (permutation[first], permutation[second])
            for first, second in topology.edges
        ),
    )


def _permuted_state(
    state: VariableGraphStateV1,
    permutation: tuple[int, ...],
) -> VariableGraphStateV1:
    ranks = [0] * len(permutation)
    for source, target in enumerate(permutation):
        ranks[target] = state.ranks[source]
    return VariableGraphStateV1(tuple(ranks), state.failure)


def _permuted_action(
    action: tuple[int, int, int],
    permutation: tuple[int, ...],
) -> tuple[int, int, int]:
    first, second = sorted((permutation[action[0]], permutation[action[1]]))
    return (first, second, permutation[action[2]])


def _atom_signature(
    atom: VariableGraphAtomV1,
) -> tuple[tuple[int, ...], bool, Fraction, Fraction]:
    return (
        atom.next_state.ranks,
        atom.failure,
        atom.probability,
        atom.normalized_reward,
    )


@dataclass(frozen=True, slots=True)
class VariableGraphPermutationControlV1:
    context_id: str
    result_id: str
    permutation: tuple[int, ...]
    checked_catalogue_count: int
    checked_ground_row_count: int
    state_coordinate_equivariance: bool
    action_coordinate_equivariance: bool
    kernel_equivariance: bool
    exact_original_failure_probability: Fraction
    exact_permuted_failure_probability: Fraction

    def __post_init__(self) -> None:
        _cid(self.context_id, "permutation-control context")
        _cid(self.result_id, "permutation-control result")
        if (
            type(self.permutation) is not tuple
            or len(self.permutation) not in TARGET_VERTEX_COUNTS
            or tuple(sorted(self.permutation))
            != tuple(range(len(self.permutation)))
            or self.permutation == tuple(range(len(self.permutation)))
            or type(self.checked_catalogue_count) is not int
            or self.checked_catalogue_count <= 0
            or type(self.checked_ground_row_count) is not int
            or self.checked_ground_row_count <= 0
            or self.state_coordinate_equivariance is not True
            or self.action_coordinate_equivariance is not True
            or self.kernel_equivariance is not True
            or type(self.exact_original_failure_probability) is not Fraction
            or self.exact_original_failure_probability
            != self.exact_permuted_failure_probability
        ):
            raise VariableOrderGraphInvariantViolation(
                "vertex permutation control is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_permutation_control.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "result_id": self.result_id,
            "permutation": list(self.permutation),
            "checked_catalogue_count": self.checked_catalogue_count,
            "checked_ground_row_count": self.checked_ground_row_count,
            "state_coordinate_equivariance": True,
            "action_coordinate_equivariance": True,
            "kernel_equivariance": True,
            "exact_original_failure_probability": _fdoc(
                self.exact_original_failure_probability
            ),
            "exact_permuted_failure_probability": _fdoc(
                self.exact_permuted_failure_probability
            ),
        }

    @property
    def control_id(self) -> str:
        return _content_id("permutation", self._payload())


def build_variable_graph_permutation_control_v1(
    result: VariableGraphContextResultV1,
    evaluation: VariableGraphMatchedEvaluationV1,
    permutation: tuple[int, ...] | None = None,
) -> VariableGraphPermutationControlV1:
    if (
        type(result) is not VariableGraphContextResultV1
        or type(evaluation) is not VariableGraphMatchedEvaluationV1
        or evaluation.result_id != result.result_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "permutation control requires an exact context result"
        )
    context = result.context
    chosen = (
        tuple(range(1, context.vertex_count)) + (0,)
        if permutation is None
        else permutation
    )
    if (
        type(chosen) is not tuple
        or tuple(sorted(chosen)) != tuple(range(context.vertex_count))
        or chosen == tuple(range(context.vertex_count))
    ):
        raise VariableOrderGraphInvariantViolation(
            "permutation control requires a nonidentity vertex bijection"
        )
    mapped_topology = _permuted_topology(context.topology, chosen)
    catalogues = (
        (result.evidence.root_rows[0].catalogue,)
        + result.evidence.continuation_catalogues
    )
    checked_rows = 0
    state_ok = True
    action_ok = True
    kernel_ok = True
    for catalogue in catalogues:
        state = catalogue.state
        mapped_state = _permuted_state(state, chosen)
        mapped_actions = tuple(
            sorted(_permuted_action(item, chosen) for item in catalogue.actions)
        )
        if mapped_actions != tuple(
            sorted(_actions_on_topology(mapped_topology, mapped_state))
        ):
            kernel_ok = False
        original_ir = _relational_state_ir(
            context.context_id,
            context.topology,
            state.ranks,
            catalogue.remaining_horizon,
            state.failure,
            catalogue.actions,
        )
        mapped_ir = _relational_state_ir(
            context.context_id,
            mapped_topology,
            mapped_state.ranks,
            catalogue.remaining_horizon,
            mapped_state.failure,
            mapped_actions,
        )
        for program in result.final_profile.state_programs:
            state_ok &= (
                evaluate_portable_state_program_v1(program, original_ir)
                == evaluate_portable_state_program_v1(program, mapped_ir)
            )
        original_slots = {
            item.opaque_action_key: item for item in original_ir.legal_actions
        }
        mapped_slots = {
            item.opaque_action_key: item for item in mapped_ir.legal_actions
        }
        for action in catalogue.actions:
            mapped_action = _permuted_action(action, chosen)
            for program in result.final_profile.action_programs:
                action_ok &= (
                    evaluate_portable_action_program_v1(
                        program,
                        original_ir,
                        original_slots[_action_key(action)],
                    )
                    == evaluate_portable_action_program_v1(
                        program,
                        mapped_ir,
                        mapped_slots[_action_key(mapped_action)],
                    )
                )
            original_atoms = RelationalGraphMergeKernelV2(context).atoms(
                state,
                action,
            )
            expected_mapped = tuple(
                sorted(
                    (
                        (
                            _permuted_state(atom.next_state, chosen).ranks,
                            atom.failure,
                            atom.probability,
                            atom.normalized_reward,
                        )
                        for atom in original_atoms
                    ),
                    key=repr,
                )
            )
            actual_mapped = tuple(
                sorted(
                    (
                        _atom_signature(atom)
                        for atom in _atoms_on_topology(
                            mapped_topology,
                            mapped_state,
                            mapped_action,
                        )
                    ),
                    key=repr,
                )
            )
            kernel_ok &= expected_mapped == actual_mapped
            checked_rows += 1
    mapped_root = _permuted_state(
        RelationalGraphMergeKernelV2(context).root_state(),
        chosen,
    )
    mapped_failure = _minimum_failure_probability_on_topology(
        mapped_topology,
        mapped_root,
        HORIZON,
        {},
    )
    return VariableGraphPermutationControlV1(
        context.context_id,
        result.result_id,
        chosen,
        len(catalogues),
        checked_rows,
        state_ok,
        action_ok,
        kernel_ok,
        evaluation.matched_direct_control.exact_root_failure_probability,
        mapped_failure,
    )


def _registered_query_id(
    context: VariableOrderGraphContextV1,
    replica_index: int,
) -> str:
    return _content_id(
        "query",
        {
            "schema": "acfqp.variable_order_graph_query.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": context.context_id,
            "replica_index": replica_index,
            "horizon": HORIZON,
            "risk_tolerance": _fdoc(context.risk_tolerance),
            "reward_semantics": "canonical_normalized_merge_reward",
        },
    )


@dataclass(frozen=True, slots=True)
class VariableGraphQueryOccurrenceV1:
    context_id: str
    query_id: str
    result_id: str
    final_model_id: str
    final_audit_id: str
    occurrence_index: int
    newly_acquired_ground_rows: int
    newly_acquired_draws: int
    identity_bound_reuse: bool

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "occurrence context"),
            (self.query_id, "occurrence query"),
            (self.result_id, "occurrence result"),
            (self.final_model_id, "occurrence final model"),
            (self.final_audit_id, "occurrence final audit"),
        ):
            _cid(value, field)
        if (
            self.occurrence_index not in (1, 2)
            or type(self.newly_acquired_ground_rows) is not int
            or self.newly_acquired_ground_rows < 0
            or type(self.newly_acquired_draws) is not int
            or self.newly_acquired_draws < 0
            or type(self.identity_bound_reuse) is not bool
            or (
                self.identity_bound_reuse
                and (
                    self.occurrence_index != 2
                    or self.newly_acquired_ground_rows != 0
                    or self.newly_acquired_draws != 0
                )
            )
            or (
                not self.identity_bound_reuse
                and (
                    self.occurrence_index != 1
                    or self.newly_acquired_ground_rows <= 0
                    or self.newly_acquired_draws <= 0
                )
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "query occurrence reuse accounting is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_query_occurrence.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "query_id": self.query_id,
            "result_id": self.result_id,
            "final_model_id": self.final_model_id,
            "final_audit_id": self.final_audit_id,
            "occurrence_index": self.occurrence_index,
            "newly_acquired_ground_rows": self.newly_acquired_ground_rows,
            "newly_acquired_draws": self.newly_acquired_draws,
            "identity_bound_reuse": self.identity_bound_reuse,
        }

    @property
    def occurrence_id(self) -> str:
        return _content_id("occurrence", self._payload())


def build_variable_graph_query_occurrences_v1(
    results: tuple[VariableGraphContextResultV1, ...],
) -> tuple[VariableGraphQueryOccurrenceV1, ...]:
    occurrences: list[VariableGraphQueryOccurrenceV1] = []
    for result in results:
        replica_count = (
            2
            if registered_graph_target_role_v1(result.context)
            is GraphTargetRole.POSITIVE
            else 1
        )
        for replica_index in range(1, replica_count + 1):
            reused = replica_index == 2
            occurrences.append(
                VariableGraphQueryOccurrenceV1(
                    result.context.context_id,
                    _registered_query_id(
                        result.context,
                        replica_index,
                    ),
                    result.result_id,
                    result.final_model.model_id,
                    result.final_audit.audit_id,
                    replica_index,
                    0
                    if reused
                    else result.evidence.ground_row_count,
                    0
                    if reused
                    else result.evidence.generative_draw_count,
                    reused,
                )
            )
    return tuple(occurrences)


@dataclass(frozen=True, slots=True)
class VariableGraphNoTransferControlV1:
    skeleton_id: str
    source_context_id: str
    target_context_id: str
    cross_order_evidence_transplant_rejected: bool
    target_log_as_source_rejected: bool
    forbidden_source_dynamics_access_rejected: bool
    tested_injections: int = 3

    def __post_init__(self) -> None:
        for value, field in (
            (self.skeleton_id, "no-transfer skeleton"),
            (self.source_context_id, "no-transfer source context"),
            (self.target_context_id, "no-transfer target context"),
        ):
            _cid(value, field)
        if (
            self.source_context_id == self.target_context_id
            or self.cross_order_evidence_transplant_rejected is not True
            or self.target_log_as_source_rejected is not True
            or self.forbidden_source_dynamics_access_rejected is not True
            or self.tested_injections != 3
        ):
            raise VariableOrderGraphInvariantViolation(
                "no-transfer/OOD control did not fail closed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_no_transfer_control.v1",
            "schema_version": SCHEMA_VERSION,
            "skeleton_id": self.skeleton_id,
            "source_context_id": self.source_context_id,
            "target_context_id": self.target_context_id,
            "cross_order_evidence_transplant_rejected": True,
            "target_log_as_source_rejected": True,
            "forbidden_source_dynamics_access_rejected": True,
            "tested_injections": 3,
        }

    @property
    def control_id(self) -> str:
        return _content_id("no_transfer", self._payload())


def run_variable_graph_no_transfer_control_v1(
    skeleton: PortableRelationalSkeletonV1,
    results: tuple[VariableGraphContextResultV1, ...],
) -> VariableGraphNoTransferControlV1:
    if (
        type(skeleton) is not PortableRelationalSkeletonV1
        or type(results) is not tuple
        or len(results) < 2
    ):
        raise VariableOrderGraphInvariantViolation(
            "no-transfer control input is invalid"
        )
    source = results[0]
    target = next(
        item
        for item in results
        if item.context.vertex_count != source.context.vertex_count
    )
    cross_rejected = False
    try:
        verify_sparse_variable_graph_evidence_v1(
            target.context,
            skeleton,
            source.evidence,
        )
    except (TypeError, ValueError):
        cross_rejected = True
    source_log_rejected = False
    try:
        verify_portable_relational_skeleton_v1(
            target_relational_observation_log_v1(
                target.context,
                target.evidence,
            ),
            skeleton,
        )
    except (TypeError, ValueError):
        source_log_rejected = True
    forbidden_access_rejected = False
    try:
        replace(
            source.evidence.access_log.events[0],
            source_dynamics_accessed=True,
        )
    except (TypeError, ValueError):
        forbidden_access_rejected = True
    return VariableGraphNoTransferControlV1(
        skeleton.skeleton_id,
        source.context.context_id,
        target.context.context_id,
        cross_rejected,
        source_log_rejected,
        forbidden_access_rejected,
    )


@dataclass(frozen=True, slots=True)
class VariableGraphCalibrationV1:
    sample_count_per_ground_row: int
    hoeffding_radius: Fraction
    per_obligation_tail_upper: Fraction
    positive_ground_rows: int
    all_ground_rows: int
    positive_atom_obligations: int
    family_atom_obligations: int
    positive_aggregate_obligations: int
    family_aggregate_obligations: int
    positive_generative_draws: int
    family_generative_draws: int
    hoeffding_exponent: Fraction
    exponential_taylor_degree: int
    exponential_taylor_lower: Fraction
    family_tail_upper: Fraction
    family_confidence_lower: Fraction
    prng_semantics_id: str = REGISTERED_PRNG_SEMANTICS_ID
    statistical_claim_scope: str = STATISTICAL_CLAIM_SCOPE
    unconditional_iid_claim: bool = False

    def __post_init__(self) -> None:
        if (
            self.sample_count_per_ground_row != SAMPLE_COUNT_PER_ROW
            or self.hoeffding_radius != HOEFFDING_RADIUS
            or self.per_obligation_tail_upper
            != PER_OBLIGATION_TAIL_UPPER
            or self.positive_ground_rows != 82
            or self.all_ground_rows != 142
            or self.positive_atom_obligations != 612
            or self.family_atom_obligations != 1092
            or type(self.positive_aggregate_obligations) is not int
            or self.positive_aggregate_obligations <= 0
            or type(self.family_aggregate_obligations) is not int
            or self.family_aggregate_obligations
            < self.positive_aggregate_obligations
            or self.positive_generative_draws != 10_747_904
            or self.family_generative_draws != 18_612_224
            or self.hoeffding_exponent != Fraction(16384, 1225)
            or self.exponential_taylor_degree != 16
            or self.exponential_taylor_lower <= 500_000
            or self.family_tail_upper
            != self.family_aggregate_obligations
            * self.per_obligation_tail_upper
            or self.family_confidence_lower != 1 - self.family_tail_upper
            or self.family_confidence_lower < Fraction(19, 20)
            or self.prng_semantics_id != REGISTERED_PRNG_SEMANTICS_ID
            or self.statistical_claim_scope != STATISTICAL_CLAIM_SCOPE
            or self.unconditional_iid_claim is not False
        ):
            raise VariableOrderGraphInvariantViolation(
                "family-wide statistical calibration changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_calibration.v1",
            "schema_version": SCHEMA_VERSION,
            "sample_count_per_ground_row": self.sample_count_per_ground_row,
            "hoeffding_radius": _fdoc(self.hoeffding_radius),
            "per_obligation_tail_upper": _fdoc(
                self.per_obligation_tail_upper
            ),
            "positive_ground_rows": self.positive_ground_rows,
            "all_ground_rows": self.all_ground_rows,
            "positive_atom_obligations": self.positive_atom_obligations,
            "family_atom_obligations": self.family_atom_obligations,
            "positive_aggregate_obligations": (
                self.positive_aggregate_obligations
            ),
            "family_aggregate_obligations": (
                self.family_aggregate_obligations
            ),
            "positive_generative_draws": self.positive_generative_draws,
            "family_generative_draws": self.family_generative_draws,
            "hoeffding_exponent": _fdoc(self.hoeffding_exponent),
            "exponential_taylor_degree": self.exponential_taylor_degree,
            "exponential_taylor_lower": _fdoc(
                self.exponential_taylor_lower
            ),
            "family_tail_upper": _fdoc(self.family_tail_upper),
            "family_confidence_lower": _fdoc(self.family_confidence_lower),
            "prng_semantics_id": self.prng_semantics_id,
            "statistical_claim_scope": self.statistical_claim_scope,
            "unconditional_iid_claim": False,
        }

    @property
    def calibration_id(self) -> str:
        return _content_id("calibration", self._payload())


def _variable_graph_calibration(
    results: tuple[VariableGraphContextResultV1, ...],
) -> VariableGraphCalibrationV1:
    positive = tuple(
        item
        for item in results
        if registered_graph_target_role_v1(item.context)
        is GraphTargetRole.POSITIVE
    )
    exponent = 2 * SAMPLE_COUNT_PER_ROW * HOEFFDING_RADIUS ** 2
    taylor = sum(
        (exponent ** power) / math.factorial(power)
        for power in range(17)
    )
    positive_aggregates = sum(
        item.evidence.preregistered_aggregate_obligation_count
        for item in positive
    )
    family_aggregates = sum(
        item.evidence.preregistered_aggregate_obligation_count
        for item in results
    )
    return VariableGraphCalibrationV1(
        SAMPLE_COUNT_PER_ROW,
        HOEFFDING_RADIUS,
        PER_OBLIGATION_TAIL_UPPER,
        sum(item.evidence.ground_row_count for item in positive),
        sum(item.evidence.ground_row_count for item in results),
        sum(item.evidence.atom_obligation_count for item in positive),
        sum(item.evidence.atom_obligation_count for item in results),
        positive_aggregates,
        family_aggregates,
        sum(item.evidence.generative_draw_count for item in positive),
        sum(item.evidence.generative_draw_count for item in results),
        exponent,
        16,
        taylor,
        family_aggregates * PER_OBLIGATION_TAIL_UPPER,
        1 - family_aggregates * PER_OBLIGATION_TAIL_UPPER,
    )


@dataclass(frozen=True, slots=True)
class VariableOrderGraphCampaignV1:
    family: VariableOrderGraphFamilyV1
    source_log: AnonymousRelationalObservationLogV1
    source_skeleton: PortableRelationalSkeletonV1
    source_metrics: PortableRelationalSynthesisMetricsV1
    results: tuple[VariableGraphContextResultV1, ...]
    evaluations: tuple[VariableGraphMatchedEvaluationV1, ...]
    permutation_controls: tuple[VariableGraphPermutationControlV1, ...]
    query_occurrences: tuple[VariableGraphQueryOccurrenceV1, ...]
    no_transfer_control: VariableGraphNoTransferControlV1
    calibration: VariableGraphCalibrationV1
    source_transition_rows_imported: int = 0
    sparse_construction_complete_closure_calls: int = 0
    fallback_exact_ground_rows: int = 0
    false_certificate_count: int = 0
    status: str = "CONDITIONAL_CROSS_ORDER_SPARSE_RAPM_CLOSED"

    def __post_init__(self) -> None:
        if (
            type(self.family) is not VariableOrderGraphFamilyV1
            or type(self.source_log) is not AnonymousRelationalObservationLogV1
            or type(self.source_skeleton) is not PortableRelationalSkeletonV1
            or type(self.source_metrics)
            is not PortableRelationalSynthesisMetricsV1
            or self.source_skeleton.source_observation_log_id
            != self.source_log.observation_log_id
            or self.source_metrics.source_observation_log_id
            != self.source_log.observation_log_id
            or self.source_metrics.skeleton_id
            != self.source_skeleton.skeleton_id
            or type(self.results) is not tuple
            or tuple(item.context for item in self.results)
            != self.family.contexts
            or any(
                type(item) is not VariableGraphContextResultV1
                for item in self.results
            )
            or type(self.evaluations) is not tuple
            or len(self.evaluations) != len(self.results)
            or any(
                type(item) is not VariableGraphMatchedEvaluationV1
                for item in self.evaluations
            )
            or tuple(item.result_id for item in self.evaluations)
            != tuple(item.result_id for item in self.results)
            or type(self.permutation_controls) is not tuple
            or len(self.permutation_controls) != len(self.results)
            or any(
                type(item) is not VariableGraphPermutationControlV1
                for item in self.permutation_controls
            )
            or tuple(item.result_id for item in self.permutation_controls)
            != tuple(item.result_id for item in self.results)
            or type(self.query_occurrences) is not tuple
            or len(self.query_occurrences) != 5
            or any(
                type(item) is not VariableGraphQueryOccurrenceV1
                for item in self.query_occurrences
            )
            or tuple(
                item.occurrence_id for item in self.query_occurrences
            )
            != tuple(
                item.occurrence_id
                for item in build_variable_graph_query_occurrences_v1(
                    self.results
                )
            )
            or type(self.no_transfer_control)
            is not VariableGraphNoTransferControlV1
            or self.no_transfer_control.skeleton_id
            != self.source_skeleton.skeleton_id
            or type(self.calibration) is not VariableGraphCalibrationV1
            or self.source_transition_rows_imported != 0
            or self.sparse_construction_complete_closure_calls != 0
            or self.fallback_exact_ground_rows
            != sum(
                0
                if item.fallback_proof is None
                else item.fallback_proof.evaluated_state_action_rows
                for item in self.results
            )
            or self.fallback_exact_ground_rows <= 0
            or self.false_certificate_count != 0
            or self.status
            != "CONDITIONAL_CROSS_ORDER_SPARSE_RAPM_CLOSED"
            or sum(
                item.terminal_outcome
                is VariableGraphTerminalOutcome.CONDITIONAL_STATISTICAL_PLAN_CERTIFICATE
                for item in self.results
            )
            != 2
            or sum(item.fallback_used for item in self.results) != 1
        ):
            raise VariableOrderGraphInvariantViolation(
                "variable-order graph campaign is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_campaign.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "family_id": self.family.family_id,
            "source_log_id": self.source_log.observation_log_id,
            "source_skeleton_id": self.source_skeleton.skeleton_id,
            "source_metrics_id": self.source_metrics.metrics_id,
            "result_ids": [item.result_id for item in self.results],
            "evaluation_ids": [
                item.evaluation_id for item in self.evaluations
            ],
            "permutation_control_ids": [
                item.control_id for item in self.permutation_controls
            ],
            "query_occurrence_ids": [
                item.occurrence_id for item in self.query_occurrences
            ],
            "no_transfer_control_id": self.no_transfer_control.control_id,
            "calibration_id": self.calibration.calibration_id,
            "source_transition_rows_imported": 0,
            "sparse_construction_complete_closure_calls": 0,
            "fallback_exact_ground_rows": self.fallback_exact_ground_rows,
            "false_certificate_count": 0,
            "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
            "status": self.status,
        }

    @property
    def campaign_id(self) -> str:
        return _content_id("campaign", self._payload())


@dataclass(frozen=True, slots=True)
class VariableOrderGraphCampaignVerificationV1:
    campaign_id: str
    verified_result_ids: tuple[str, ...]
    verified_raw_replay_ids: tuple[str, ...]
    verified_evaluation_ids: tuple[str, ...]
    verified_permutation_control_ids: tuple[str, ...]
    verified_occurrence_ids: tuple[str, ...]
    verified_no_transfer_control_id: str
    positive_certificate_count: int
    exact_fallback_count: int
    source_skeleton_replay_passed: bool
    typed_identity_chain_passed: bool
    no_transfer_boundary_passed: bool
    sparse_access_boundary_passed: bool

    def __post_init__(self) -> None:
        _cid(self.campaign_id, "campaign verification campaign")
        for field in (
            self.verified_result_ids,
            self.verified_raw_replay_ids,
            self.verified_evaluation_ids,
            self.verified_permutation_control_ids,
            self.verified_occurrence_ids,
        ):
            if type(field) is not tuple or not field:
                raise VariableOrderGraphInvariantViolation(
                    "campaign verification has an empty identity chain"
                )
            for item in field:
                _cid(item, "campaign verification artifact")
        _cid(
            self.verified_no_transfer_control_id,
            "campaign verification no-transfer control",
        )
        if (
            self.positive_certificate_count != 2
            or self.exact_fallback_count != 1
            or self.source_skeleton_replay_passed is not True
            or self.typed_identity_chain_passed is not True
            or self.no_transfer_boundary_passed is not True
            or self.sparse_access_boundary_passed is not True
        ):
            raise VariableOrderGraphInvariantViolation(
                "campaign verification did not close every obligation"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.variable_order_graph_campaign_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "campaign_id": self.campaign_id,
            "verified_result_ids": list(self.verified_result_ids),
            "verified_raw_replay_ids": list(self.verified_raw_replay_ids),
            "verified_evaluation_ids": list(
                self.verified_evaluation_ids
            ),
            "verified_permutation_control_ids": list(
                self.verified_permutation_control_ids
            ),
            "verified_occurrence_ids": list(self.verified_occurrence_ids),
            "verified_no_transfer_control_id": (
                self.verified_no_transfer_control_id
            ),
            "positive_certificate_count": self.positive_certificate_count,
            "exact_fallback_count": self.exact_fallback_count,
            "source_skeleton_replay_passed": True,
            "typed_identity_chain_passed": True,
            "no_transfer_boundary_passed": True,
            "sparse_access_boundary_passed": True,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("campaign_verification", self._payload())


@functools.lru_cache(maxsize=1)
def verify_variable_order_graph_campaign_v1(
    campaign: VariableOrderGraphCampaignV1,
) -> VariableOrderGraphCampaignVerificationV1:
    if type(campaign) is not VariableOrderGraphCampaignV1:
        raise VariableOrderGraphInvariantViolation(
            "campaign verifier rejects runtime substitutions"
        )
    verify_portable_relational_skeleton_v1(
        campaign.source_log,
        campaign.source_skeleton,
    )
    replayed_metrics = portable_relational_synthesis_metrics_v1(
        campaign.source_log,
        campaign.source_skeleton,
    )
    if replayed_metrics.metrics_id != campaign.source_metrics.metrics_id:
        raise VariableOrderGraphInvariantViolation(
            "source synthesis metrics failed replay"
        )
    for result, evaluation, permutation_control in zip(
        campaign.results,
        campaign.evaluations,
        campaign.permutation_controls,
    ):
        raw_replay = verify_sparse_variable_graph_evidence_v1(
            result.context,
            campaign.source_skeleton,
            result.evidence,
        )
        if (
            raw_replay.verification_id
            != result.verification.verification_id
            or result.evidence.preregistered_aggregate_obligation_count
            != _preregistered_aggregate_obligation_count(
                result.context,
                campaign.source_skeleton,
                result.evidence.root_rows
                + result.evidence.continuation_rows,
            )
            or
            result.verification.evidence_id != result.evidence.evidence_id
            or result.verification.replayed_ground_rows
            != result.evidence.ground_row_count
            or result.verification.replayed_draws
            != result.evidence.generative_draw_count
            or result.evidence.source_dynamics_rows_used != 0
            or result.evidence.complete_target_closure_rows_used != 0
            or any(
                item.complete_closure_accessed
                or item.source_registry_accessed
                or item.source_dynamics_accessed
                for item in result.evidence.access_log.events
            )
        ):
            raise VariableOrderGraphInvariantViolation(
                "evidence verification or sparse boundary failed"
            )
        expected_base_profile = _base_coordinate_profile(
            campaign.source_skeleton
        )
        expected_base_model = build_partial_statistical_rapm_v1(
            result.context,
            campaign.source_skeleton,
            expected_base_profile,
            result.evidence,
            result.verification,
        )
        expected_base_audit = audit_partial_statistical_rapm_v1(
            result.context,
            expected_base_profile,
            expected_base_model,
            result.evidence,
        )
        if (
            expected_base_profile.profile_id != result.base_profile.profile_id
            or expected_base_model.model_id != result.base_model.model_id
            or expected_base_audit.audit_id != result.base_audit.audit_id
        ):
            raise VariableOrderGraphInvariantViolation(
                "base RAPM proof failed semantic replay"
            )
        if result.program_trace is None:
            if (
                result.final_profile.profile_id
                != result.base_profile.profile_id
                or result.final_model.model_id != result.base_model.model_id
                or result.final_audit.audit_id != result.base_audit.audit_id
            ):
                raise VariableOrderGraphInvariantViolation(
                    "base-certified result changed its final proof"
                )
        else:
            (
                trace,
                final_profile,
                final_model,
                final_audit,
            ) = generate_and_test_target_graph_programs_v1(
                result.context,
                campaign.source_skeleton,
                expected_base_profile,
                expected_base_model,
                expected_base_audit,
                result.evidence,
                result.verification,
            )
            if (
                trace.trace_id != result.program_trace.trace_id
                or (
                    final_profile is None
                    and result.program_trace.sound_cover_found
                )
                or (
                    final_profile is not None
                    and (
                        final_profile.profile_id
                        != result.final_profile.profile_id
                        or final_model is None
                        or final_model.model_id != result.final_model.model_id
                        or final_audit is None
                        or final_audit.audit_id != result.final_audit.audit_id
                    )
                )
            ):
                raise VariableOrderGraphInvariantViolation(
                    "target program trace failed semantic replay"
                )
        if result.fallback_proof is not None:
            fallback = execute_exact_ground_fallback_v1(
                result.context,
                result.final_audit,
            )
            if fallback.proof_id != result.fallback_proof.proof_id:
                raise VariableOrderGraphInvariantViolation(
                    "exact fallback proof failed replay"
                )
        elif (
            result.final_audit.outcome
            is not PortableGraphAuditOutcome.CONDITIONALLY_CERTIFIED
        ):
            raise VariableOrderGraphInvariantViolation(
                "failed abstract result omitted its fallback"
            )
        expected_evaluation = evaluate_variable_graph_context_v1(result)
        if expected_evaluation.evaluation_id != evaluation.evaluation_id:
            raise VariableOrderGraphInvariantViolation(
                "matched direct evaluation failed replay"
            )
        expected_permutation = build_variable_graph_permutation_control_v1(
            result,
            evaluation,
            permutation_control.permutation,
        )
        if expected_permutation.control_id != permutation_control.control_id:
            raise VariableOrderGraphInvariantViolation(
                "vertex-permutation control failed replay"
            )
    expected_calibration = _variable_graph_calibration(campaign.results)
    if expected_calibration.calibration_id != campaign.calibration.calibration_id:
        raise VariableOrderGraphInvariantViolation(
            "campaign calibration failed replay"
        )
    expected_occurrences = build_variable_graph_query_occurrences_v1(
        campaign.results
    )
    if tuple(
        item.occurrence_id for item in expected_occurrences
    ) != tuple(item.occurrence_id for item in campaign.query_occurrences):
        raise VariableOrderGraphInvariantViolation(
            "query occurrence reuse chain failed replay"
        )
    expected_no_transfer = run_variable_graph_no_transfer_control_v1(
        campaign.source_skeleton,
        campaign.results,
    )
    if (
        expected_no_transfer.control_id
        != campaign.no_transfer_control.control_id
    ):
        raise VariableOrderGraphInvariantViolation(
            "no-transfer/OOD injection control failed replay"
        )
    return VariableOrderGraphCampaignVerificationV1(
        campaign.campaign_id,
        tuple(item.result_id for item in campaign.results),
        tuple(item.verification.verification_id for item in campaign.results),
        tuple(item.evaluation_id for item in campaign.evaluations),
        tuple(item.control_id for item in campaign.permutation_controls),
        tuple(
            item.occurrence_id for item in campaign.query_occurrences
        ),
        campaign.no_transfer_control.control_id,
        2,
        1,
        True,
        True,
        True,
        True,
    )


@functools.lru_cache(maxsize=1)
def run_variable_order_graph_campaign_v1(
) -> VariableOrderGraphCampaignV1:
    family = registered_variable_order_family_v1()
    source_log = portable_graph_source_log_v1()
    skeleton = portable_graph_source_skeleton_v1()
    metrics = portable_graph_source_metrics_v1()
    results = tuple(
        run_variable_graph_context_v1(context, skeleton)
        for context in family.contexts
    )
    evaluations = tuple(
        evaluate_variable_graph_context_v1(item) for item in results
    )
    permutation_controls = tuple(
        build_variable_graph_permutation_control_v1(item, evaluation)
        for item, evaluation in zip(results, evaluations)
    )
    occurrences = build_variable_graph_query_occurrences_v1(results)
    no_transfer = run_variable_graph_no_transfer_control_v1(
        skeleton,
        results,
    )
    fallback_rows = sum(
        0
        if item.fallback_proof is None
        else item.fallback_proof.evaluated_state_action_rows
        for item in results
    )
    campaign = VariableOrderGraphCampaignV1(
        family,
        source_log,
        skeleton,
        metrics,
        results,
        evaluations,
        permutation_controls,
        occurrences,
        no_transfer,
        _variable_graph_calibration(results),
        0,
        0,
        fallback_rows,
    )
    verify_variable_order_graph_campaign_v1(campaign)
    return campaign


__all__ = [
    "AbstractPolicyAssignmentV1",
    "AccessKind",
    "CONTRACT_VERSION",
    "ExactGroundFallbackProofV1",
    "GraphTargetRole",
    "GroundConcretizerEntryV1",
    "GroundPolicyAssignmentV1",
    "HORIZON",
    "HOEFFDING_RADIUS",
    "K6_EDGES",
    "K6_MINUS_EDGE_EDGES",
    "NO_COVER_RISK_TOLERANCE",
    "ObservedVariableGraphAtomV1",
    "PER_OBLIGATION_TAIL_UPPER",
    "POSITIVE_RISK_TOLERANCE",
    "PROFILE_KEY",
    "REGISTERED_PRNG_SEMANTICS_ID",
    "RootConeAuthorizationV1",
    "PackedVariableGraphRowV1",
    "PartialStatisticalRAPMV1",
    "PortableGraphAuditOutcome",
    "PortableGraphAuditV1",
    "PortableGraphCoordinateProfileV1",
    "RelationalGraphMergeKernelV2",
    "SAMPLE_COUNT_PER_ROW",
    "SOURCE_VERTEX_COUNTS",
    "STATISTICAL_CLAIM_SCOPE",
    "SparseAccessEventV1",
    "SparseAccessLogV1",
    "SparseCoverageCertificateV1",
    "SparseEvidenceVerificationV1",
    "SparseVariableGraphEvidenceV1",
    "TARGET_VERTEX_COUNTS",
    "TargetGraphProgramTraceV1",
    "VariableGraphCalibrationV1",
    "VariableGraphColdControlV1",
    "VariableGraphContextResultV1",
    "VariableGraphMatchedEvaluationV1",
    "VariableGraphNoTransferControlV1",
    "VariableGraphPermutationControlV1",
    "VariableGraphQueryOccurrenceV1",
    "VariableGraphStateV1",
    "VariableGraphTerminalOutcome",
    "VariableOrderGraphCampaignV1",
    "VariableOrderGraphCampaignVerificationV1",
    "VariableOrderGraphContextV1",
    "VariableOrderGraphFamilyV1",
    "VariableOrderGraphInvariantViolation",
    "W5_EDGES",
    "acquire_sparse_variable_graph_evidence_v1",
    "audit_partial_statistical_rapm_v1",
    "build_partial_statistical_rapm_v1",
    "build_portable_graph_source_log_v1",
    "build_variable_graph_query_occurrences_v1",
    "build_variable_graph_permutation_control_v1",
    "cold_variable_graph_control_v1",
    "evaluate_variable_graph_context_v1",
    "exact_rejection_ordinal_v1",
    "execute_exact_ground_fallback_v1",
    "generate_and_test_target_graph_programs_v1",
    "portable_graph_source_log_v1",
    "portable_graph_source_metrics_v1",
    "portable_graph_source_skeleton_v1",
    "registered_variable_order_contexts_v1",
    "registered_variable_order_family_v1",
    "run_variable_graph_context_v1",
    "run_variable_graph_no_transfer_control_v1",
    "run_variable_order_graph_campaign_v1",
    "target_relational_observation_log_v1",
    "verify_packed_variable_graph_row_v1",
    "verify_sparse_variable_graph_evidence_v1",
    "verify_variable_order_graph_campaign_v1",
]
