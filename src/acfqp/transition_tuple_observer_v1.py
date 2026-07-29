"""Opaque target-local graph transition observations for V0-068.

The operational boundary in this module intentionally exposes less than the
V0-067 acquisition runner:

* public contexts contain topology, root state, horizon, and risk only;
* legal ground actions are available exactly;
* a target-local draw returns the realized joint transition tuple;
* no operational object contains an outcome ordinal, support cardinality,
  support descriptor table, or transition probability.

The environment law is private to the observation authority.  The
operational sampler implements that law directly and never calls either the
legacy ``RelationalGraphMergeKernelV2.atoms`` method or the evaluation-only
enumerator below.  Discovery and validation use domain-separated streams.
Their deterministic seeds bind the same state, action, and frozen support
epoch, so quotient and direct consumers receive paired draws without a route
label entering the seed.

``evaluation_exact_atoms_v1`` and ``evaluation_exact_ground_search_v1`` are
explicitly evaluation-only authorities.  They expose the hidden law and must
not be imported by an operational planner.
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
from itertools import combinations
from threading import RLock
from typing import Any, Callable, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp.relational_graph_core_v1 import GraphTopologyV1


SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = "1.32.0"
PROFILE_KEY = "opaque_graph_transition_observer_v0"
REGISTERED_HORIZON = 2
REGISTERED_RANK_CAP = 6
REGISTERED_REWARD_CEILING = Fraction(3, 64)
REGISTERED_NORMALIZED_REGRET_TOLERANCE = Fraction(1, 20)
REGISTERED_OBSERVER_SEMANTICS_ID = (
    "opaque_joint_transition_splitmix64_rejection_v1"
)
REGISTERED_RANDOMNESS_IMPLEMENTATION = (
    "DETERMINISTIC_SPLITMIX64_COUNTER_REPLAY_BENCHMARK"
)
EXACT_IID_IMPLEMENTATION_CLAIMED = False
STATISTICAL_CLAIM_SCOPE = (
    "CONDITIONAL_ON_IDEALIZED_TARGET_LOCAL_UINT64_IID_AUTHORITY_"
    "NOT_PROVEN_BY_DETERMINISTIC_REPLAY_IMPLEMENTATION"
)

_RANK_CAP = REGISTERED_RANK_CAP
_REWARD_NORMALIZER = Fraction(REGISTERED_HORIZON)
_UINT64_MODULUS = 1 << 64
_UINT64_MASK = _UINT64_MODULUS - 1
_SPLITMIX_GAMMA = 0x9E3779B97F4A7C15


class TransitionTupleObserverInvariantViolation(ValueError):
    """A public identity, stream binding, tuple, or replay is invalid."""


DOMAIN_TAGS = {
    "context": "acfqp:opaque-graph-public-context:v1",
    "state": "acfqp:opaque-graph-symbolic-state:v1",
    "catalogue": "acfqp:opaque-graph-legal-action-catalogue:v1",
    "support_set": "acfqp:opaque-graph-frozen-support-set:v1",
    "support_epoch": "acfqp:opaque-graph-support-epoch:v1",
    "stream": "acfqp:opaque-graph-target-local-stream:v1",
    "raw_digest": "acfqp:opaque-graph-raw-draw-digest:v1",
    "raw_commitment": "acfqp:opaque-graph-raw-draw-commitment:v1",
    "observation": "acfqp:opaque-graph-joint-transition-observation:v1",
    "work": "acfqp:opaque-graph-transition-stream-work:v1",
    "replay": "acfqp:opaque-graph-transition-replay:v1",
    "evaluation_atom": "acfqp:evaluation-only-graph-exact-atom:v1",
    "evaluation_assignment": (
        "acfqp:evaluation-only-graph-policy-assignment:v1"
    ),
    "evaluation_search": "acfqp:evaluation-only-graph-ground-search:v1",
}

_STREAM_SEED_DOMAINS = {
    "DISCOVERY": "acfqp:opaque-graph-discovery-stream-seed:v1",
    "VALIDATION": "acfqp:opaque-graph-validation-stream-seed:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):  # pragma: no cover
    raise RuntimeError("opaque observer content domains must be unique")
if len(_STREAM_SEED_DOMAINS) != len(set(_STREAM_SEED_DOMAINS.values())):
    raise RuntimeError("opaque observer stream domains must be unique")


def _content_id(
    role: str,
    payload: Mapping[str, Any],
    raw_suffix: bytes = b"",
) -> str:
    try:
        tag = DOMAIN_TAGS[role].encode("utf-8")
        encoded = canonical_json_bytes(dict(payload))
    except (KeyError, TypeError, ValueError) as error:
        raise TransitionTupleObserverInvariantViolation(str(error)) from error
    body = tag + b"\x00" + encoded
    if raw_suffix:
        body += b"\x00" + raw_suffix
    return hashlib.sha256(body).hexdigest()


_ID_MEMO_MAX_ENTRIES = 65_536
_ID_MEMO: OrderedDict[tuple[str, tuple[Any, ...]], str] = OrderedDict()
_ID_MEMO_LOCK = RLock()


def _memoized_content_id(
    role: str,
    key: tuple[Any, ...],
    payload_factory: Callable[[], Mapping[str, Any]],
) -> str:
    """Memoize pure content IDs without retaining full transition objects."""

    cache_key = (role, key)
    with _ID_MEMO_LOCK:
        cached = _ID_MEMO.get(cache_key)
        if cached is not None:
            _ID_MEMO.move_to_end(cache_key)
            return cached
    computed = _content_id(role, payload_factory())
    with _ID_MEMO_LOCK:
        prior = _ID_MEMO.setdefault(cache_key, computed)
        if prior != computed:  # pragma: no cover - SHA/domain determinism guard
            raise TransitionTupleObserverInvariantViolation(
                "one observer ID memo key produced two content identities"
            )
        _ID_MEMO.move_to_end(cache_key)
        while len(_ID_MEMO) > _ID_MEMO_MAX_ENTRIES:
            _ID_MEMO.popitem(last=False)
        return prior


def clear_transition_tuple_observer_id_cache_v1() -> None:
    """Clear execution-only ID memoization; artifact bytes remain unchanged."""

    with _ID_MEMO_LOCK:
        _ID_MEMO.clear()


def _cid(value: Any, field: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise TransitionTupleObserverInvariantViolation(
            f"{field} must be a full content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    exact = Fraction(value)
    return {
        "numerator": exact.numerator,
        "denominator": exact.denominator,
    }


def _action(value: Any, field: str = "action") -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
    ):
        raise TransitionTupleObserverInvariantViolation(
            f"{field} must be an exact integer triple"
        )
    return value


def _sorted_content_ids(
    values: Iterable[str],
    field: str,
) -> tuple[str, ...]:
    if type(values) not in (tuple, list):
        raise TransitionTupleObserverInvariantViolation(
            f"{field} must be a concrete sequence"
        )
    output = tuple(values)
    for value in output:
        _cid(value, field)
    if output != tuple(sorted(set(output))):
        raise TransitionTupleObserverInvariantViolation(
            f"{field} must be unique and content-ID sorted"
        )
    return output


def _graph_edges(
    rows: Iterable[tuple[int, int]],
) -> tuple[tuple[int, int], ...]:
    return tuple(sorted({tuple(sorted(item)) for item in rows}))


_W5_EDGES = _graph_edges(
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
_K6_EDGES = tuple(combinations(range(6), 2))
_K6_MINUS_EDGE_EDGES = tuple(
    edge for edge in combinations(range(6), 2) if edge != (4, 5)
)

_PUBLIC_CONTEXT_SPECS = {
    "opaque_graph_w5_v0": (
        GraphTopologyV1(5, _W5_EDGES),
        (1, 1, 2, 0, 0),
        Fraction(1, 20),
    ),
    "opaque_graph_k6_v0": (
        GraphTopologyV1(6, _K6_EDGES),
        (1, 1, 2, 0, 0, 0),
        Fraction(1, 20),
    ),
    "opaque_graph_k6_minus_edge_v0": (
        GraphTopologyV1(6, _K6_MINUS_EDGE_EDGES),
        (0, 2, 1, 1, 0, 0),
        # Registered between the exact ground optimum 2277/16000 and
        # the base quotient lift 11393/80000.  The context is therefore
        # a genuine feasible-ground/no-sound-partial-cover fallback control.
        Fraction(2847, 20000),
    ),
}

# This is environment-authority state, not public context metadata.  The
# operational observer consumes it privately, while the explicit
# evaluation-only boundary below may reveal it.
_HIDDEN_SPAWN_LAWS = {
    "opaque_graph_w5_v0": (
        (1, Fraction(99, 100)),
        (2, Fraction(1, 100)),
    ),
    "opaque_graph_k6_v0": (
        (1, Fraction(197, 200)),
        (2, Fraction(1, 100)),
        (3, Fraction(1, 200)),
    ),
    "opaque_graph_k6_minus_edge_v0": (
        (1, Fraction(99, 100)),
        (2, Fraction(1, 100)),
    ),
}


@dataclass(frozen=True, slots=True)
class PublicGraphContextV1:
    """The complete public context; it contains no environment law fields."""

    context_key: str
    topology: GraphTopologyV1
    root_ranks: tuple[int, ...]
    horizon: int
    risk_tolerance: Fraction
    rank_cap: int = REGISTERED_RANK_CAP
    reward_ceiling: Fraction = REGISTERED_REWARD_CEILING
    normalized_regret_tolerance: Fraction = (
        REGISTERED_NORMALIZED_REGRET_TOLERANCE
    )

    def __post_init__(self) -> None:
        registered = _PUBLIC_CONTEXT_SPECS.get(self.context_key)
        if (
            type(self.context_key) is not str
            or type(self.topology) is not GraphTopologyV1
            or type(self.root_ranks) is not tuple
            or any(type(item) is not int for item in self.root_ranks)
            or type(self.horizon) is not int
            or self.horizon != REGISTERED_HORIZON
            or type(self.risk_tolerance) is not Fraction
            or self.rank_cap != REGISTERED_RANK_CAP
            or self.reward_ceiling != REGISTERED_REWARD_CEILING
            or self.normalized_regret_tolerance
            != REGISTERED_NORMALIZED_REGRET_TOLERANCE
            or registered
            != (self.topology, self.root_ranks, self.risk_tolerance)
        ):
            raise TransitionTupleObserverInvariantViolation(
                "public graph context is not exactly registered"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_public_context.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "context_key": self.context_key,
            "topology": self.topology.to_document(),
            "root_ranks": list(self.root_ranks),
            "horizon": self.horizon,
            "risk_tolerance": _fdoc(self.risk_tolerance),
            "rank_cap": self.rank_cap,
            "reward_ceiling": _fdoc(self.reward_ceiling),
            "normalized_regret_tolerance": _fdoc(
                self.normalized_regret_tolerance
            ),
            "observer_semantics_id": REGISTERED_OBSERVER_SEMANTICS_ID,
            "randomness_implementation": REGISTERED_RANDOMNESS_IMPLEMENTATION,
            "exact_iid_implementation_claimed": False,
            "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
        }

    @property
    def context_id(self) -> str:
        return _memoized_content_id(
            "context",
            (
                self.context_key,
                self.topology.topology_id,
                self.root_ranks,
                self.horizon,
                self.risk_tolerance,
                self.rank_cap,
                self.reward_ceiling,
                self.normalized_regret_tolerance,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "context_id": self.context_id}


def registered_public_graph_contexts_v1(
) -> tuple[PublicGraphContextV1, ...]:
    """Return the three law-free registered target contexts."""

    return tuple(
        PublicGraphContextV1(
            key,
            topology,
            root,
            REGISTERED_HORIZON,
            risk,
        )
        for key, (topology, root, risk) in _PUBLIC_CONTEXT_SPECS.items()
    )


def public_context_by_key_v1(context_key: str) -> PublicGraphContextV1:
    if type(context_key) is not str:
        raise TransitionTupleObserverInvariantViolation(
            "public context key must be an exact string"
        )
    for context in registered_public_graph_contexts_v1():
        if context.context_key == context_key:
            return context
    raise TransitionTupleObserverInvariantViolation(
        "public context key is not registered"
    )


def _registered_context(context: Any) -> PublicGraphContextV1:
    if (
        type(context) is not PublicGraphContextV1
        or context not in registered_public_graph_contexts_v1()
    ):
        raise TransitionTupleObserverInvariantViolation(
            "operation requires an exact registered public context"
        )
    return context


@dataclass(frozen=True, slots=True)
class SymbolicGraphStateV1:
    """A directly observed symbolic board, without a transition descriptor."""

    ranks: tuple[int, ...]
    failure: bool = False

    def __post_init__(self) -> None:
        if (
            type(self.ranks) is not tuple
            or len(self.ranks) not in (5, 6)
            or any(
                type(rank) is not int or not 0 <= rank <= _RANK_CAP
                for rank in self.ranks
            )
            or type(self.failure) is not bool
        ):
            raise TransitionTupleObserverInvariantViolation(
                "symbolic graph state is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_symbolic_state.v1",
            "schema_version": SCHEMA_VERSION,
            "ranks": list(self.ranks),
            "failure": self.failure,
        }

    @property
    def state_id(self) -> str:
        return _memoized_content_id(
            "state",
            (self.ranks, self.failure),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "state_id": self.state_id}


def root_state_v1(context: PublicGraphContextV1) -> SymbolicGraphStateV1:
    registered = _registered_context(context)
    return SymbolicGraphStateV1(registered.root_ranks)


def _validate_state_in_context(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
) -> None:
    if (
        type(state) is not SymbolicGraphStateV1
        or len(state.ranks) != context.topology.vertex_count
    ):
        raise TransitionTupleObserverInvariantViolation(
            "symbolic state is outside its public graph context"
        )


def _legal_actions(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
) -> tuple[tuple[int, int, int], ...]:
    _validate_state_in_context(context, state)
    if state.failure:
        return ()
    return tuple(
        (first, second, survivor)
        for first, second in context.topology.edges
        if state.ranks[first] > 0
        and state.ranks[first] == state.ranks[second]
        for survivor in (first, second)
    )


@dataclass(frozen=True, slots=True)
class LegalActionCatalogueV1:
    context_id: str
    state: SymbolicGraphStateV1
    remaining_horizon: int
    actions: tuple[tuple[int, int, int], ...]

    def __post_init__(self) -> None:
        _cid(self.context_id, "catalogue context")
        if (
            type(self.state) is not SymbolicGraphStateV1
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, REGISTERED_HORIZON)
            or type(self.actions) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 3
                or any(type(value) is not int for value in item)
                for item in self.actions
            )
            or self.actions != tuple(sorted(set(self.actions)))
            or (self.state.failure and self.actions)
        ):
            raise TransitionTupleObserverInvariantViolation(
                "legal action catalogue is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_legal_action_catalogue.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "state": self.state.to_document(),
            "remaining_horizon": self.remaining_horizon,
            "actions": [list(item) for item in self.actions],
        }

    @property
    def catalogue_id(self) -> str:
        return _memoized_content_id(
            "catalogue",
            (
                self.context_id,
                self.state.state_id,
                self.remaining_horizon,
                self.actions,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "catalogue_id": self.catalogue_id}


def legal_action_catalogue_v1(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
    remaining_horizon: int,
) -> LegalActionCatalogueV1:
    registered = _registered_context(context)
    _validate_state_in_context(registered, state)
    if (
        type(remaining_horizon) is not int
        or remaining_horizon not in (1, REGISTERED_HORIZON)
    ):
        raise TransitionTupleObserverInvariantViolation(
            "remaining horizon is outside the registered H=2 query"
        )
    actions = _legal_actions(registered, state)
    if state.failure != (not actions):
        raise TransitionTupleObserverInvariantViolation(
            "state failure flag disagrees with exact legal actions"
        )
    return LegalActionCatalogueV1(
        registered.context_id,
        state,
        remaining_horizon,
        actions,
    )


def _validated_catalogue(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
) -> LegalActionCatalogueV1:
    if (
        type(catalogue) is not LegalActionCatalogueV1
        or catalogue.context_id != context.context_id
    ):
        raise TransitionTupleObserverInvariantViolation(
            "catalogue/public-context identity mismatch"
        )
    expected = legal_action_catalogue_v1(
        context,
        catalogue.state,
        catalogue.remaining_horizon,
    )
    if catalogue.to_document() != expected.to_document():
        raise TransitionTupleObserverInvariantViolation(
            "catalogue is not the canonical exact legal-action catalogue"
        )
    return catalogue


@dataclass(frozen=True, slots=True)
class SupportEpochIdentityV1:
    """A stream epoch bound only to an opaque frozen-support commitment."""

    context_id: str
    epoch_index: int
    frozen_support_set_id: str
    parent_epoch_id: str | None

    def __post_init__(self) -> None:
        _cid(self.context_id, "support epoch context")
        _cid(self.frozen_support_set_id, "frozen support set")
        if (
            type(self.epoch_index) is not int
            or self.epoch_index < 0
            or (
                self.parent_epoch_id is not None
                and type(self.parent_epoch_id) is not str
            )
        ):
            raise TransitionTupleObserverInvariantViolation(
                "support epoch identity is invalid"
            )
        if self.epoch_index == 0:
            if self.parent_epoch_id is not None:
                raise TransitionTupleObserverInvariantViolation(
                    "root support epoch cannot have a parent"
                )
        else:
            if self.parent_epoch_id is None:
                raise TransitionTupleObserverInvariantViolation(
                    "nonroot support epoch requires a parent"
                )
            _cid(self.parent_epoch_id, "parent support epoch")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_support_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "epoch_index": self.epoch_index,
            "frozen_support_set_id": self.frozen_support_set_id,
            "parent_epoch": (
                {"kind": "ROOT"}
                if self.parent_epoch_id is None
                else {
                    "kind": "PREDECESSOR",
                    "epoch_id": self.parent_epoch_id,
                }
            ),
        }

    @property
    def epoch_id(self) -> str:
        return _memoized_content_id(
            "support_epoch",
            (
                self.context_id,
                self.epoch_index,
                self.frozen_support_set_id,
                self.parent_epoch_id,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "epoch_id": self.epoch_id}


def support_epoch_identity_v1(
    context: PublicGraphContextV1,
    epoch_index: int,
    frozen_support_member_ids: tuple[str, ...] = (),
    parent_epoch: SupportEpochIdentityV1 | None = None,
) -> SupportEpochIdentityV1:
    """Freeze a support-set commitment without serializing its members."""

    registered = _registered_context(context)
    members = _sorted_content_ids(
        frozen_support_member_ids,
        "frozen support member IDs",
    )
    if type(epoch_index) is not int or epoch_index < 0:
        raise TransitionTupleObserverInvariantViolation(
            "support epoch index must be a nonnegative integer"
        )
    if epoch_index == 0:
        if parent_epoch is not None:
            raise TransitionTupleObserverInvariantViolation(
                "root support epoch cannot bind a parent object"
            )
        parent_id = None
    else:
        if (
            type(parent_epoch) is not SupportEpochIdentityV1
            or parent_epoch.context_id != registered.context_id
            or parent_epoch.epoch_index != epoch_index - 1
        ):
            raise TransitionTupleObserverInvariantViolation(
                "support epoch parent is not the immediate same-context epoch"
            )
        parent_id = parent_epoch.epoch_id
    support_set_id = _content_id(
        "support_set",
        {
            "schema": "acfqp.opaque_graph_frozen_support_set.v1",
            "schema_version": SCHEMA_VERSION,
            "member_ids": list(members),
        },
    )
    return SupportEpochIdentityV1(
        registered.context_id,
        epoch_index,
        support_set_id,
        parent_id,
    )


class ObservationLane(str, Enum):
    DISCOVERY = "DISCOVERY"
    VALIDATION = "VALIDATION"


@dataclass(frozen=True, slots=True)
class RawDrawCommitmentV1:
    stream_id: str
    accepted_draw_index: int
    random_word_start_index: int
    random_word_count: int
    rejection_count: int
    raw_digest: str

    def __post_init__(self) -> None:
        _cid(self.stream_id, "raw commitment stream")
        _cid(self.raw_digest, "raw draw digest")
        if (
            type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or type(self.random_word_start_index) is not int
            or self.random_word_start_index <= 0
            or type(self.random_word_count) is not int
            or self.random_word_count <= 0
            or type(self.rejection_count) is not int
            or self.rejection_count < 0
            or self.random_word_count != self.rejection_count + 1
        ):
            raise TransitionTupleObserverInvariantViolation(
                "raw draw commitment counters do not reconcile"
            )

    @property
    def random_word_end_index(self) -> int:
        return self.random_word_start_index + self.random_word_count - 1

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_raw_draw_commitment.v1",
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "accepted_draw_index": self.accepted_draw_index,
            "random_word_start_index": self.random_word_start_index,
            "random_word_end_index": self.random_word_end_index,
            "random_word_count": self.random_word_count,
            "rejection_count": self.rejection_count,
            "raw_digest": self.raw_digest,
        }

    @property
    def commitment_id(self) -> str:
        return _memoized_content_id(
            "raw_commitment",
            (
                self.stream_id,
                self.accepted_draw_index,
                self.random_word_start_index,
                self.random_word_count,
                self.rejection_count,
                self.raw_digest,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "commitment_id": self.commitment_id}


@dataclass(frozen=True, slots=True)
class ObservedJointTransitionV1:
    """One complete observed tuple, with no support-level metadata."""

    context_id: str
    catalogue_id: str
    support_epoch_id: str
    lane: ObservationLane
    stream_id: str
    source_state: SymbolicGraphStateV1
    action: tuple[int, int, int]
    remaining_horizon: int
    accepted_draw_index: int
    next_state: SymbolicGraphStateV1
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    raw_commitment: RawDrawCommitmentV1

    def __post_init__(self) -> None:
        for value, field in (
            (self.context_id, "observation context"),
            (self.catalogue_id, "observation catalogue"),
            (self.support_epoch_id, "observation support epoch"),
            (self.stream_id, "observation stream"),
        ):
            _cid(value, field)
        _action(self.action)
        if (
            type(self.lane) is not ObservationLane
            or type(self.source_state) is not SymbolicGraphStateV1
            or type(self.next_state) is not SymbolicGraphStateV1
            or len(self.source_state.ranks) != len(self.next_state.ranks)
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, REGISTERED_HORIZON)
            or type(self.accepted_draw_index) is not int
            or self.accepted_draw_index <= 0
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or self.terminal
            != (self.failure or self.remaining_horizon == 1)
            or type(self.raw_commitment) is not RawDrawCommitmentV1
            or self.raw_commitment.stream_id != self.stream_id
            or self.raw_commitment.accepted_draw_index
            != self.accepted_draw_index
        ):
            raise TransitionTupleObserverInvariantViolation(
                "observed joint transition is internally inconsistent"
            )

    @property
    def joint_tuple(
        self,
    ) -> tuple[
        SymbolicGraphStateV1,
        Fraction,
        bool,
        bool,
        RawDrawCommitmentV1,
    ]:
        return (
            self.next_state,
            self.realized_row_reward,
            self.failure,
            self.terminal,
            self.raw_commitment,
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_joint_transition_observation.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "support_epoch_id": self.support_epoch_id,
            "lane": self.lane.value,
            "stream_id": self.stream_id,
            "source_state": self.source_state.to_document(),
            "action": list(self.action),
            "remaining_horizon": self.remaining_horizon,
            "accepted_draw_index": self.accepted_draw_index,
            "next_state": self.next_state.to_document(),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "raw_commitment": self.raw_commitment.to_document(),
        }

    @property
    def observation_id(self) -> str:
        return _memoized_content_id(
            "observation",
            (
                self.context_id,
                self.catalogue_id,
                self.support_epoch_id,
                self.lane.value,
                self.stream_id,
                self.source_state.state_id,
                self.action,
                self.remaining_horizon,
                self.accepted_draw_index,
                self.next_state.state_id,
                self.realized_row_reward,
                self.failure,
                self.terminal,
                self.raw_commitment.commitment_id,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "observation_id": self.observation_id}


@dataclass(frozen=True, slots=True)
class TransitionStreamWorkV1:
    stream_id: str
    accepted_draws: int
    random_word_calls: int
    rejection_count: int

    def __post_init__(self) -> None:
        _cid(self.stream_id, "stream work stream")
        if (
            type(self.accepted_draws) is not int
            or self.accepted_draws < 0
            or type(self.random_word_calls) is not int
            or self.random_word_calls < 0
            or type(self.rejection_count) is not int
            or self.rejection_count < 0
            or self.random_word_calls
            != self.accepted_draws + self.rejection_count
        ):
            raise TransitionTupleObserverInvariantViolation(
                "stream work counters do not reconcile"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_transition_stream_work.v1",
            "schema_version": SCHEMA_VERSION,
            "stream_id": self.stream_id,
            "accepted_draws": self.accepted_draws,
            "random_word_calls": self.random_word_calls,
            "rejection_count": self.rejection_count,
        }

    @property
    def work_id(self) -> str:
        return _memoized_content_id(
            "work",
            (
                self.stream_id,
                self.accepted_draws,
                self.random_word_calls,
                self.rejection_count,
            ),
            self._payload,
        )

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "work_id": self.work_id}


def _splitmix64(value: int) -> int:
    value &= _UINT64_MASK
    value = (value ^ (value >> 30)) * 0xBF58476D1CE4E5B9
    value &= _UINT64_MASK
    value = (value ^ (value >> 27)) * 0x94D049BB133111EB
    value &= _UINT64_MASK
    return value ^ (value >> 31)


def _stream_payload(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: ObservationLane,
    support_epoch: SupportEpochIdentityV1,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.opaque_graph_target_local_stream.v1",
        "schema_version": SCHEMA_VERSION,
        "contract_version": CONTRACT_VERSION,
        "observer_semantics_id": REGISTERED_OBSERVER_SEMANTICS_ID,
        "randomness_implementation": REGISTERED_RANDOMNESS_IMPLEMENTATION,
        "exact_iid_implementation_claimed": False,
        "statistical_claim_scope": STATISTICAL_CLAIM_SCOPE,
        "context_id": context.context_id,
        "catalogue_id": catalogue.catalogue_id,
        "state_id": catalogue.state.state_id,
        "remaining_horizon": catalogue.remaining_horizon,
        "action": list(action),
        "lane": lane.value,
        "support_epoch_id": support_epoch.epoch_id,
    }


def _stream_id(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: ObservationLane,
    support_epoch: SupportEpochIdentityV1,
) -> str:
    return _content_id(
        "stream",
        _stream_payload(
            context,
            catalogue,
            action,
            lane,
            support_epoch,
        ),
    )


def _stream_seed(stream_id: str, lane: ObservationLane) -> int:
    domain = _STREAM_SEED_DOMAINS[lane.value].encode("utf-8")
    return int.from_bytes(
        hashlib.sha256(domain + b"\x00" + stream_id.encode("ascii")).digest()[
            :8
        ],
        "big",
    )


def _merge_row(
    context: PublicGraphContextV1,
    state: SymbolicGraphStateV1,
    action: tuple[int, int, int],
) -> tuple[list[int], tuple[int, ...], Fraction]:
    if action not in _legal_actions(context, state):
        raise TransitionTupleObserverInvariantViolation(
            "transition stream action is not legal at its source state"
        )
    first, second, survivor = action
    rank = state.ranks[first]
    board = list(state.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, _RANK_CAP)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    if not empty:
        raise TransitionTupleObserverInvariantViolation(
            "registered merge produced no spawn location"
        )
    reward = (
        Fraction(2 ** (rank + 1), 2 ** (_RANK_CAP + 1))
        / _REWARD_NORMALIZER
    )
    return board, empty, reward


def _hidden_law(
    context: PublicGraphContextV1,
) -> tuple[tuple[int, Fraction], ...]:
    try:
        law = _HIDDEN_SPAWN_LAWS[context.context_key]
    except KeyError as error:  # pragma: no cover - context registry prevents it
        raise TransitionTupleObserverInvariantViolation(
            "observation authority has no hidden law for this context"
        ) from error
    if sum((probability for _, probability in law), Fraction(0)) != 1:
        raise RuntimeError("hidden spawn law is not normalized")
    return law


def _integer_hidden_law(
    context: PublicGraphContextV1,
) -> tuple[int, tuple[tuple[int, int], ...]]:
    law = _hidden_law(context)
    denominator = 1
    for _, probability in law:
        denominator = (
            denominator
            * probability.denominator
            // _greatest_common_divisor(
                denominator,
                probability.denominator,
            )
        )
    integer_law = tuple(
        (rank, probability.numerator * (denominator // probability.denominator))
        for rank, probability in law
    )
    if sum(weight for _, weight in integer_law) != denominator:
        raise RuntimeError("hidden integer law does not normalize")
    return denominator, integer_law


def _greatest_common_divisor(first: int, second: int) -> int:
    while second:
        first, second = second, first % second
    return first


def _rank_from_token(
    integer_law: tuple[tuple[int, int], ...],
    token: int,
) -> int:
    cursor = 0
    for rank, weight in integer_law:
        cursor += weight
        if token < cursor:
            return rank
    raise RuntimeError("accepted rank token lies outside the hidden law")


def _raw_draw_digest(
    *,
    stream_id: str,
    accepted_draw_index: int,
    random_word_start_index: int,
    next_state: SymbolicGraphStateV1,
    reward: Fraction,
    failure: bool,
    terminal: bool,
    words: tuple[int, ...],
) -> str:
    payload = {
        "schema": "acfqp.opaque_graph_raw_draw_digest.v1",
        "schema_version": SCHEMA_VERSION,
        "stream_id": stream_id,
        "accepted_draw_index": accepted_draw_index,
        "random_word_start_index": random_word_start_index,
        "random_word_count": len(words),
        "next_state": next_state.to_document(),
        "realized_row_reward": _fdoc(reward),
        "failure": failure,
        "terminal": terminal,
    }
    raw = b"".join(word.to_bytes(8, "big") for word in words)
    return _content_id("raw_digest", payload, raw)


def _validate_stream_binding(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: ObservationLane,
    support_epoch: SupportEpochIdentityV1,
) -> tuple[
    PublicGraphContextV1,
    LegalActionCatalogueV1,
    tuple[int, int, int],
    ObservationLane,
    SupportEpochIdentityV1,
]:
    registered = _registered_context(context)
    canonical_catalogue = _validated_catalogue(registered, catalogue)
    canonical_action = _action(action)
    if canonical_action not in canonical_catalogue.actions:
        raise TransitionTupleObserverInvariantViolation(
            "stream action is outside the exact legal-action catalogue"
        )
    if type(lane) is not ObservationLane:
        raise TransitionTupleObserverInvariantViolation(
            "stream lane must be DISCOVERY or VALIDATION"
        )
    if (
        type(support_epoch) is not SupportEpochIdentityV1
        or support_epoch.context_id != registered.context_id
    ):
        raise TransitionTupleObserverInvariantViolation(
            "support epoch/public-context identity mismatch"
        )
    return (
        registered,
        canonical_catalogue,
        canonical_action,
        lane,
        support_epoch,
    )


class OpaqueTargetLocalTransitionStreamV1:
    """Mutable observer handle; only immutable draw artifacts leave it."""

    __slots__ = (
        "_context",
        "_catalogue",
        "_action",
        "_lane",
        "_support_epoch",
        "_stream_id",
        "_seed",
        "_merged_board",
        "_empty_cells",
        "_reward",
        "_law_denominator",
        "_integer_law",
        "_outcome_denominator",
        "_acceptance_limit",
        "_successor_cache",
        "_accepted_draws",
        "_random_word_calls",
        "_rejection_count",
    )

    def __init__(
        self,
        context: PublicGraphContextV1,
        catalogue: LegalActionCatalogueV1,
        action: tuple[int, int, int],
        lane: ObservationLane,
        support_epoch: SupportEpochIdentityV1,
    ) -> None:
        (
            self._context,
            self._catalogue,
            self._action,
            self._lane,
            self._support_epoch,
        ) = _validate_stream_binding(
            context,
            catalogue,
            action,
            lane,
            support_epoch,
        )
        self._stream_id = _stream_id(
            self._context,
            self._catalogue,
            self._action,
            self._lane,
            self._support_epoch,
        )
        self._seed = _stream_seed(self._stream_id, self._lane)
        merged_board, empty_cells, reward = _merge_row(
            self._context,
            self._catalogue.state,
            self._action,
        )
        law_denominator, integer_law = _integer_hidden_law(self._context)
        outcome_denominator = len(empty_cells) * law_denominator
        self._merged_board = tuple(merged_board)
        self._empty_cells = empty_cells
        self._reward = reward
        self._law_denominator = law_denominator
        self._integer_law = integer_law
        self._outcome_denominator = outcome_denominator
        self._acceptance_limit = (
            _UINT64_MODULUS
            - (_UINT64_MODULUS % outcome_denominator)
        )
        self._successor_cache: dict[
            tuple[int, int],
            tuple[SymbolicGraphStateV1, bool, bool],
        ] = {}
        self._accepted_draws = 0
        self._random_word_calls = 0
        self._rejection_count = 0

    @property
    def stream_id(self) -> str:
        return self._stream_id

    @property
    def accepted_draw_count(self) -> int:
        return self._accepted_draws

    @property
    def random_word_calls(self) -> int:
        return self._random_word_calls

    @property
    def rejection_count(self) -> int:
        return self._rejection_count

    def work_snapshot(self) -> TransitionStreamWorkV1:
        return TransitionStreamWorkV1(
            self._stream_id,
            self._accepted_draws,
            self._random_word_calls,
            self._rejection_count,
        )

    def draw(self) -> ObservedJointTransitionV1:
        """Return one opaque joint tuple from the private environment law."""

        start = self._random_word_calls + 1
        words: list[int] = []
        while True:
            word_index = self._random_word_calls + 1
            word = _splitmix64(
                self._seed + _SPLITMIX_GAMMA * word_index
            )
            self._random_word_calls += 1
            words.append(word)
            if word >= self._acceptance_limit:
                self._rejection_count += 1
                continue
            token = word % self._outcome_denominator
            empty_index = token // self._law_denominator
            rank_token = token % self._law_denominator
            spawn_rank = _rank_from_token(
                self._integer_law,
                rank_token,
            )
            break
        outcome_key = (empty_index, spawn_rank)
        outcome = self._successor_cache.get(outcome_key)
        if outcome is None:
            successor = list(self._merged_board)
            successor[self._empty_cells[empty_index]] = spawn_rank
            provisional = SymbolicGraphStateV1(tuple(successor))
            failure = not _legal_actions(self._context, provisional)
            next_state = SymbolicGraphStateV1(tuple(successor), failure)
            terminal = failure or self._catalogue.remaining_horizon == 1
            outcome = (next_state, failure, terminal)
            self._successor_cache[outcome_key] = outcome
        else:
            next_state, failure, terminal = outcome
        self._accepted_draws += 1
        digest = _raw_draw_digest(
            stream_id=self._stream_id,
            accepted_draw_index=self._accepted_draws,
            random_word_start_index=start,
            next_state=next_state,
            reward=self._reward,
            failure=failure,
            terminal=terminal,
            words=tuple(words),
        )
        commitment = RawDrawCommitmentV1(
            self._stream_id,
            self._accepted_draws,
            start,
            len(words),
            len(words) - 1,
            digest,
        )
        return ObservedJointTransitionV1(
            self._context.context_id,
            self._catalogue.catalogue_id,
            self._support_epoch.epoch_id,
            self._lane,
            self._stream_id,
            self._catalogue.state,
            self._action,
            self._catalogue.remaining_horizon,
            self._accepted_draws,
            next_state,
            self._reward,
            failure,
            terminal,
            commitment,
        )


def open_target_local_transition_stream_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: ObservationLane,
    support_epoch: SupportEpochIdentityV1,
) -> OpaqueTargetLocalTransitionStreamV1:
    return OpaqueTargetLocalTransitionStreamV1(
        context,
        catalogue,
        action,
        lane,
        support_epoch,
    )


@dataclass(frozen=True, slots=True)
class TransitionReplayVerificationV1:
    observation_id: str
    stream_id: str
    replayed_accepted_draws: int
    replayed_random_word_calls: int
    replayed_rejections: int
    tuple_replay_passed: bool = True
    execution_lane: str = "TRUSTED_OBSERVATION_REPLAY"

    def __post_init__(self) -> None:
        _cid(self.observation_id, "replay observation")
        _cid(self.stream_id, "replay stream")
        if (
            type(self.replayed_accepted_draws) is not int
            or self.replayed_accepted_draws <= 0
            or type(self.replayed_random_word_calls) is not int
            or self.replayed_random_word_calls
            < self.replayed_accepted_draws
            or type(self.replayed_rejections) is not int
            or self.replayed_rejections < 0
            or self.replayed_random_word_calls
            != self.replayed_accepted_draws + self.replayed_rejections
            or self.tuple_replay_passed is not True
            or self.execution_lane != "TRUSTED_OBSERVATION_REPLAY"
        ):
            raise TransitionTupleObserverInvariantViolation(
                "transition replay verification is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.opaque_graph_transition_replay.v1",
            "schema_version": SCHEMA_VERSION,
            "observation_id": self.observation_id,
            "stream_id": self.stream_id,
            "replayed_accepted_draws": self.replayed_accepted_draws,
            "replayed_random_word_calls": self.replayed_random_word_calls,
            "replayed_rejections": self.replayed_rejections,
            "tuple_replay_passed": True,
            "execution_lane": self.execution_lane,
        }

    @property
    def verification_id(self) -> str:
        return _content_id("replay", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "verification_id": self.verification_id}


def verify_observed_transition_tuple_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
    lane: ObservationLane,
    support_epoch: SupportEpochIdentityV1,
    observation: ObservedJointTransitionV1,
) -> TransitionReplayVerificationV1:
    if type(observation) is not ObservedJointTransitionV1:
        raise TransitionTupleObserverInvariantViolation(
            "transition replay rejects a noncanonical observation"
        )
    stream = open_target_local_transition_stream_v1(
        context,
        catalogue,
        action,
        lane,
        support_epoch,
    )
    if (
        observation.context_id != context.context_id
        or observation.catalogue_id != catalogue.catalogue_id
        or observation.support_epoch_id != support_epoch.epoch_id
        or observation.stream_id != stream.stream_id
        or observation.lane is not lane
    ):
        raise TransitionTupleObserverInvariantViolation(
            "observation identity does not match the replay authority"
        )
    replayed: ObservedJointTransitionV1 | None = None
    for _ in range(observation.accepted_draw_index):
        replayed = stream.draw()
    if (
        replayed is None
        or replayed.to_document() != observation.to_document()
    ):
        raise TransitionTupleObserverInvariantViolation(
            "observed joint tuple differs from deterministic raw replay"
        )
    work = stream.work_snapshot()
    return TransitionReplayVerificationV1(
        observation.observation_id,
        stream.stream_id,
        work.accepted_draws,
        work.random_word_calls,
        work.rejection_count,
    )


@dataclass(frozen=True, slots=True)
class EvaluationExactAtomV1:
    """One hidden-law atom; this type is evaluation/fallback only."""

    context_id: str
    catalogue_id: str
    action: tuple[int, int, int]
    next_state: SymbolicGraphStateV1
    probability: Fraction
    realized_row_reward: Fraction
    failure: bool
    terminal: bool
    execution_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        _cid(self.context_id, "evaluation atom context")
        _cid(self.catalogue_id, "evaluation atom catalogue")
        _action(self.action)
        if (
            type(self.next_state) is not SymbolicGraphStateV1
            or type(self.probability) is not Fraction
            or not 0 < self.probability <= 1
            or type(self.realized_row_reward) is not Fraction
            or not 0 <= self.realized_row_reward <= 1
            or type(self.failure) is not bool
            or self.failure != self.next_state.failure
            or type(self.terminal) is not bool
            or self.execution_lane != "EVALUATION_ONLY"
        ):
            raise TransitionTupleObserverInvariantViolation(
                "evaluation-only exact atom is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.evaluation_only_graph_exact_atom.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.context_id,
            "catalogue_id": self.catalogue_id,
            "action": list(self.action),
            "next_state": self.next_state.to_document(),
            "probability": _fdoc(self.probability),
            "realized_row_reward": _fdoc(self.realized_row_reward),
            "failure": self.failure,
            "terminal": self.terminal,
            "execution_lane": self.execution_lane,
        }

    @property
    def atom_id(self) -> str:
        return _content_id("evaluation_atom", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "atom_id": self.atom_id}


def _enumerate_hidden_atoms_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[EvaluationExactAtomV1, ...]:
    board, empty, reward = _merge_row(
        context,
        catalogue.state,
        action,
    )
    law = _hidden_law(context)
    atoms: list[EvaluationExactAtomV1] = []
    for cell in empty:
        for spawn_rank, rank_probability in law:
            successor = board.copy()
            successor[cell] = spawn_rank
            provisional = SymbolicGraphStateV1(tuple(successor))
            failure = not _legal_actions(context, provisional)
            next_state = SymbolicGraphStateV1(tuple(successor), failure)
            atoms.append(
                EvaluationExactAtomV1(
                    context.context_id,
                    catalogue.catalogue_id,
                    action,
                    next_state,
                    Fraction(1, len(empty)) * rank_probability,
                    reward,
                    failure,
                    failure or catalogue.remaining_horizon == 1,
                )
            )
    if sum((atom.probability for atom in atoms), Fraction(0)) != 1:
        raise RuntimeError("evaluation-only exact atom row is not normalized")
    return tuple(atoms)


def evaluation_exact_atoms_v1(
    context: PublicGraphContextV1,
    catalogue: LegalActionCatalogueV1,
    action: tuple[int, int, int],
) -> tuple[EvaluationExactAtomV1, ...]:
    """Reveal one exact hidden-law row in the evaluation/fallback lane."""

    registered = _registered_context(context)
    canonical_catalogue = _validated_catalogue(registered, catalogue)
    canonical_action = _action(action)
    if canonical_action not in canonical_catalogue.actions:
        raise TransitionTupleObserverInvariantViolation(
            "evaluation atom action is outside the legal catalogue"
        )
    return _enumerate_hidden_atoms_v1(
        registered,
        canonical_catalogue,
        canonical_action,
    )


@dataclass(frozen=True, slots=True)
class EvaluationGroundPolicyAssignmentV1:
    state: SymbolicGraphStateV1
    remaining_horizon: int
    action: tuple[int, int, int]
    failure_probability: Fraction
    normalized_reward: Fraction
    execution_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        _action(self.action)
        if (
            type(self.state) is not SymbolicGraphStateV1
            or type(self.remaining_horizon) is not int
            or self.remaining_horizon not in (1, REGISTERED_HORIZON)
            or type(self.failure_probability) is not Fraction
            or not 0 <= self.failure_probability <= 1
            or type(self.normalized_reward) is not Fraction
            or not 0 <= self.normalized_reward <= 1
            or self.execution_lane != "EVALUATION_ONLY"
        ):
            raise TransitionTupleObserverInvariantViolation(
                "evaluation-only policy assignment is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.evaluation_only_graph_policy_assignment.v1",
            "schema_version": SCHEMA_VERSION,
            "state": self.state.to_document(),
            "remaining_horizon": self.remaining_horizon,
            "action": list(self.action),
            "failure_probability": _fdoc(self.failure_probability),
            "normalized_reward": _fdoc(self.normalized_reward),
            "execution_lane": self.execution_lane,
        }

    @property
    def assignment_id(self) -> str:
        return _content_id("evaluation_assignment", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "assignment_id": self.assignment_id}


@dataclass(frozen=True, slots=True)
class EvaluationExactGroundSearchV1:
    context_id: str
    policy_assignments: tuple[EvaluationGroundPolicyAssignmentV1, ...]
    root_failure_probability: Fraction
    root_normalized_reward: Fraction
    evaluated_state_action_rows: int
    feasible_under_public_risk: bool
    complete_h2_deterministic_policy_search: bool = True
    execution_lane: str = "EVALUATION_ONLY"

    def __post_init__(self) -> None:
        _cid(self.context_id, "evaluation search context")
        if (
            type(self.policy_assignments) is not tuple
            or not self.policy_assignments
            or any(
                type(item) is not EvaluationGroundPolicyAssignmentV1
                for item in self.policy_assignments
            )
            or type(self.root_failure_probability) is not Fraction
            or not 0 <= self.root_failure_probability <= 1
            or type(self.root_normalized_reward) is not Fraction
            or not 0 <= self.root_normalized_reward <= 1
            or type(self.evaluated_state_action_rows) is not int
            or self.evaluated_state_action_rows <= 0
            or self.feasible_under_public_risk is not True
            or self.complete_h2_deterministic_policy_search is not True
            or self.execution_lane != "EVALUATION_ONLY"
        ):
            raise TransitionTupleObserverInvariantViolation(
                "evaluation-only exact ground search is invalid"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.evaluation_only_graph_ground_search.v1",
            "schema_version": SCHEMA_VERSION,
            "contract_version": CONTRACT_VERSION,
            "context_id": self.context_id,
            "policy_assignments": [
                item.to_document() for item in self.policy_assignments
            ],
            "root_failure_probability": _fdoc(
                self.root_failure_probability
            ),
            "root_normalized_reward": _fdoc(self.root_normalized_reward),
            "evaluated_state_action_rows": self.evaluated_state_action_rows,
            "feasible_under_public_risk": True,
            "complete_h2_deterministic_policy_search": True,
            "execution_lane": self.execution_lane,
        }

    @property
    def search_id(self) -> str:
        return _content_id("evaluation_search", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "search_id": self.search_id}


@dataclass(frozen=True, slots=True)
class _PolicyOption:
    risk: Fraction
    reward: Fraction
    assignments: tuple[EvaluationGroundPolicyAssignmentV1, ...]


def _assignment_signature(
    assignments: tuple[EvaluationGroundPolicyAssignmentV1, ...],
) -> tuple[tuple[str, int, tuple[int, int, int]], ...]:
    return tuple(
        sorted(
            (
                item.state.state_id,
                item.remaining_horizon,
                item.action,
            )
            for item in assignments
        )
    )


def _pareto_policy_options(
    options: Iterable[_PolicyOption],
) -> tuple[_PolicyOption, ...]:
    deduplicated: dict[
        tuple[Fraction, Fraction],
        _PolicyOption,
    ] = {}
    for option in options:
        key = (option.risk, option.reward)
        current = deduplicated.get(key)
        if (
            current is None
            or _assignment_signature(option.assignments)
            < _assignment_signature(current.assignments)
        ):
            deduplicated[key] = option
    rows = tuple(deduplicated.values())
    retained = tuple(
        option
        for option in rows
        if not any(
            other.risk <= option.risk
            and other.reward >= option.reward
            and (
                other.risk < option.risk
                or other.reward > option.reward
            )
            for other in rows
        )
    )
    return tuple(
        sorted(
            retained,
            key=lambda item: (
                item.risk,
                -item.reward,
                _assignment_signature(item.assignments),
            ),
        )
    )


def evaluation_exact_ground_search_v1(
    context: PublicGraphContextV1,
) -> EvaluationExactGroundSearchV1:
    """Exhaust the registered H=2 deterministic policy family exactly."""

    registered = _registered_context(context)
    root = root_state_v1(registered)
    root_catalogue = legal_action_catalogue_v1(
        registered,
        root,
        REGISTERED_HORIZON,
    )
    evaluated_rows: set[
        tuple[str, int, tuple[int, int, int]]
    ] = set()
    leaf_cache: dict[str, tuple[_PolicyOption, ...]] = {}

    def leaf_options(state: SymbolicGraphStateV1) -> tuple[_PolicyOption, ...]:
        cached = leaf_cache.get(state.state_id)
        if cached is not None:
            return cached
        catalogue = legal_action_catalogue_v1(registered, state, 1)
        options: list[_PolicyOption] = []
        for action in catalogue.actions:
            evaluated_rows.add((state.state_id, 1, action))
            atoms = evaluation_exact_atoms_v1(
                registered,
                catalogue,
                action,
            )
            reward = atoms[0].realized_row_reward
            if any(item.realized_row_reward != reward for item in atoms):
                raise RuntimeError("registered row reward became stochastic")
            risk = sum(
                (
                    item.probability
                    for item in atoms
                    if item.failure
                ),
                Fraction(0),
            )
            assignment = EvaluationGroundPolicyAssignmentV1(
                state,
                1,
                action,
                risk,
                reward,
            )
            options.append(_PolicyOption(risk, reward, (assignment,)))
        retained = _pareto_policy_options(options)
        if not retained:
            raise RuntimeError("nonfailure leaf state has no policy option")
        leaf_cache[state.state_id] = retained
        return retained

    root_options: list[_PolicyOption] = []
    for root_action in root_catalogue.actions:
        evaluated_rows.add(
            (root.state_id, REGISTERED_HORIZON, root_action)
        )
        atoms = evaluation_exact_atoms_v1(
            registered,
            root_catalogue,
            root_action,
        )
        immediate_reward = atoms[0].realized_row_reward
        if any(
            item.realized_row_reward != immediate_reward for item in atoms
        ):
            raise RuntimeError("registered root reward became stochastic")
        immediate_risk = sum(
            (
                item.probability
                for item in atoms
                if item.failure
            ),
            Fraction(0),
        )
        child_mass: dict[str, Fraction] = {}
        child_state: dict[str, SymbolicGraphStateV1] = {}
        for atom in atoms:
            if atom.failure:
                continue
            child_mass[atom.next_state.state_id] = (
                child_mass.get(atom.next_state.state_id, Fraction(0))
                + atom.probability
            )
            child_state[atom.next_state.state_id] = atom.next_state
        partial = (
            _PolicyOption(
                immediate_risk,
                immediate_reward,
                (),
            ),
        )
        for state_id in sorted(child_mass):
            mass = child_mass[state_id]
            expanded: list[_PolicyOption] = []
            for prefix in partial:
                for child in leaf_options(child_state[state_id]):
                    expanded.append(
                        _PolicyOption(
                            prefix.risk + mass * child.risk,
                            prefix.reward + mass * child.reward,
                            prefix.assignments + child.assignments,
                        )
                    )
            partial = _pareto_policy_options(expanded)
        for option in partial:
            root_assignment = EvaluationGroundPolicyAssignmentV1(
                root,
                REGISTERED_HORIZON,
                root_action,
                option.risk,
                option.reward,
            )
            root_options.append(
                _PolicyOption(
                    option.risk,
                    option.reward,
                    (root_assignment, *option.assignments),
                )
            )
    feasible = tuple(
        option
        for option in _pareto_policy_options(root_options)
        if option.risk <= registered.risk_tolerance
    )
    if not feasible:
        raise TransitionTupleObserverInvariantViolation(
            "registered H=2 query has no feasible deterministic policy"
        )
    selected = min(
        feasible,
        key=lambda item: (
            -item.reward,
            item.risk,
            _assignment_signature(item.assignments),
        ),
    )
    assignments = tuple(
        sorted(
            selected.assignments,
            key=lambda item: (
                -item.remaining_horizon,
                item.state.state_id,
                item.action,
            ),
        )
    )
    return EvaluationExactGroundSearchV1(
        registered.context_id,
        assignments,
        selected.risk,
        selected.reward,
        len(evaluated_rows),
        True,
    )


__all__ = [
    "CONTRACT_VERSION",
    "EXACT_IID_IMPLEMENTATION_CLAIMED",
    "EvaluationExactAtomV1",
    "EvaluationExactGroundSearchV1",
    "EvaluationGroundPolicyAssignmentV1",
    "LegalActionCatalogueV1",
    "ObservationLane",
    "ObservedJointTransitionV1",
    "OpaqueTargetLocalTransitionStreamV1",
    "PROFILE_KEY",
    "PublicGraphContextV1",
    "REGISTERED_HORIZON",
    "REGISTERED_NORMALIZED_REGRET_TOLERANCE",
    "REGISTERED_OBSERVER_SEMANTICS_ID",
    "REGISTERED_RANDOMNESS_IMPLEMENTATION",
    "REGISTERED_RANK_CAP",
    "REGISTERED_REWARD_CEILING",
    "RawDrawCommitmentV1",
    "SCHEMA_VERSION",
    "STATISTICAL_CLAIM_SCOPE",
    "SupportEpochIdentityV1",
    "SymbolicGraphStateV1",
    "TransitionReplayVerificationV1",
    "TransitionStreamWorkV1",
    "TransitionTupleObserverInvariantViolation",
    "evaluation_exact_atoms_v1",
    "evaluation_exact_ground_search_v1",
    "clear_transition_tuple_observer_id_cache_v1",
    "legal_action_catalogue_v1",
    "open_target_local_transition_stream_v1",
    "public_context_by_key_v1",
    "registered_public_graph_contexts_v1",
    "root_state_v1",
    "support_epoch_identity_v1",
    "verify_observed_transition_tuple_v1",
]
