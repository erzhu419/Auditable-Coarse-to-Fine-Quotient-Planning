"""Law-free learned support graph and exact H=2 robust planners for V0-075.

The component closes four previously separate construction obligations:

* reconstruct a typed partial state/action/support graph from a route-native
  statistical model, with complete actions only at materialized states;
* prove that every learned outcome is structurally possible without reading a
  transition law;
* compile an observation-driven probabilistic-bisimulation quotient with a
  fixed uniform distinct-action concretizer; and
* solve the resulting H=2 interval model, or the matched ground model, with
  exact rational arithmetic and a deterministic finite-horizon policy.

Only public graph semantics and the statistical artifacts emitted by
``v075_route_native_backend_core_v1`` are consumed.  In particular, this
module has no observer, kernel, private reveal, salt, signer, random tape,
exact transition atom, callback, cache, or resume surface.

``OTHER`` is never silently renormalized away.  At H=2 it receives the
registered absorbing policy-abort continuation (failure one, continuation
reward zero); at H=1 it has the same policy-abort failure semantics.  The
immediate deterministic merge reward remains earned before the abort.
An observed positive H=2 successor whose H=1 catalogue has not yet been
materialized is treated identically to ``OTHER`` for planning.  It is not
silently promoted into an active decision node and does not force complete
target closure before a useful partial model can exist.

The planners return operational *candidates*.  A plan certificate still
requires the disjoint independent exact total-lift authority.  Production
integration consequently remains false until the batch-to-route adapter,
worker registry, and exact-lift caller are bound by the final
preregistration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from fractions import Fraction
import hashlib
import itertools
from typing import Any, Iterable, Mapping

from acfqp.phase3e_ids import canonical_json_bytes, parse_content_id
from acfqp import v075_public_campaign_authority_v1 as public_authority
from acfqp import v075_public_graph_semantics_v1 as public_graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as backend


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.40.0"
PROFILE_KEY = "v075_learned_support_quotient_planners_v1"

POLICY_ABORT_RULE = (
    "OTHER_IS_ABSORBING_POLICY_ABORT_FAILURE_WITH_ZERO_CONTINUATION_REWARD"
)
MAX_EXACT_POLICY_ASSIGNMENTS = 1_000_000
PRODUCTION_INTEGRATION_READY = False
SCIENTIFIC_CERTIFICATE_ISSUANCE_ALLOWED = False

DOMAIN_TAGS = {
    "state_node": "acfqp:v075-learned-support-state-node:v1",
    "support_graph": "acfqp:v075-learned-support-graph:v1",
    "row_behavior": "acfqp:v075-learned-row-behavior:v1",
    "cell": "acfqp:v075-observation-driven-quotient-cell:v1",
    "concretizer": (
        "acfqp:v075-observation-driven-distinct-action-concretizer:v1"
    ),
    "semantic_action": (
        "acfqp:v075-observation-driven-semantic-action:v1"
    ),
    "quotient": "acfqp:v075-observation-driven-quotient:v1",
    "decision": "acfqp:v075-robust-h2-policy-decision:v1",
    "policy": "acfqp:v075-robust-h2-deterministic-policy:v1",
    "envelope": "acfqp:v075-robust-h2-operational-envelope:v1",
    "counter": "acfqp:v075-support-planner-counter:v1",
    "work": "acfqp:v075-support-planner-work:v1",
    "result": "acfqp:v075-support-planner-result:v1",
}

if (
    len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values()))
    or any(not value.startswith("acfqp:v075-") for value in DOMAIN_TAGS.values())
):
    raise RuntimeError("V0-075 support/planner domains must be unique")


class V075LearnedSupportPlannerInvariantViolation(ValueError):
    """A learned graph, quotient, interval, policy, or identity is invalid."""


def _fail(message: str) -> None:
    raise V075LearnedSupportPlannerInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075LearnedSupportPlannerInvariantViolation(str(error)) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075LearnedSupportPlannerInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _fdoc(value: Fraction) -> dict[str, int]:
    if type(value) is not Fraction:
        _fail("support/planner arithmetic must use exact Fraction")
    return {"numerator": value.numerator, "denominator": value.denominator}


def _action(
    value: Any,
    field_name: str = "ground action",
) -> tuple[int, int, int]:
    if (
        type(value) is not tuple
        or len(value) != 3
        or any(type(item) is not int for item in value)
        or value[0] >= value[1]
        or value[2] not in value[:2]
    ):
        _fail(f"{field_name} is not one canonical merge/survivor action")
    return value


def _registered_context(
    context_id: str,
) -> public_authority.V075PublicReplicateContextV1:
    _cid(context_id, "learned support context")
    result = tuple(
        item
        for item in (
            public_authority.freeze_v075_public_family_generation_v1()
            .replicate_contexts
        )
        if item.context_id == context_id
    )
    if len(result) != 1:
        _fail("learned support context is not preregistered")
    return result[0]


def _merge_reward(
    context: public_authority.V075PublicReplicateContextV1,
    state: public_graph.V075SymbolicGraphStateV1,
    action: tuple[int, int, int],
) -> Fraction:
    canonical = _action(action)
    if canonical not in public_graph.legal_action_triples_v1(
        context,
        state.ranks,
        state.failure,
    ):
        _fail("learned row action is illegal at its reconstructed source")
    rank = state.ranks[canonical[0]]
    return (
        Fraction(2 ** (rank + 1), 2 ** (context.rank_cap + 1))
        / context.horizon
    )


def _structural_successor(
    *,
    context: public_authority.V075PublicReplicateContextV1,
    source: public_graph.V075SymbolicGraphStateV1,
    action: tuple[int, int, int],
    descriptor: backend.V075OutcomeDescriptorV1,
    remaining_horizon: int,
) -> public_graph.V075SymbolicGraphStateV1:
    """Reconstruct one outcome using geometry only, never a spawn law."""

    canonical = _action(action)
    if descriptor.context_id != context.context_id:
        _fail("outcome descriptor was transplanted across contexts")
    if canonical not in public_graph.legal_action_triples_v1(
        context,
        source.ranks,
        source.failure,
    ):
        _fail("outcome descriptor has an illegal source action")
    first, second, survivor = canonical
    rank = source.ranks[first]
    board = list(source.ranks)
    board[first] = 0
    board[second] = 0
    board[survivor] = min(rank + 1, context.rank_cap)
    empty = tuple(index for index, value in enumerate(board) if value == 0)
    changed = tuple(
        index
        for index, (before, after) in enumerate(
            zip(board, descriptor.next_ranks)
        )
        if before != after
    )
    if (
        len(changed) != 1
        or changed[0] not in empty
        or board[changed[0]] != 0
        or not 0 < descriptor.next_ranks[changed[0]] <= context.rank_cap
    ):
        _fail(
            "learned outcome is not one structurally possible post-merge "
            "single spawn"
        )
    try:
        successor = public_graph.V075SymbolicGraphStateV1(
            context,
            descriptor.next_ranks,
            descriptor.failure,
        )
    except public_graph.V075PublicGraphSemanticsInvariantViolation as error:
        raise V075LearnedSupportPlannerInvariantViolation(str(error)) from error
    if (
        successor.state_id != descriptor.next_state_id
        or descriptor.terminal
        != (descriptor.failure or remaining_horizon == 1)
        or descriptor.realized_row_reward
        != _merge_reward(context, source, canonical)
    ):
        _fail("learned outcome state, terminal, or reward semantics changed")
    return successor


def _validate_intervals(row: backend.V075StatisticalRowV1) -> None:
    if not row.validation_capability_ids:
        _fail("learned support graph requires a validation epoch for every row")
    if (
        tuple(item.event_key for item in row.intervals)
        != tuple(item.descriptor_id for item in row.support) + ("OTHER",)
    ):
        _fail("row intervals are not support-plus-OTHER")
    draw_counts = {item.draw_count for item in row.intervals}
    if len(draw_counts) != 1:
        _fail("one row epoch has inconsistent event draw counts")
    draw_count = next(iter(draw_counts))
    if sum(item.success_count for item in row.intervals) != draw_count:
        _fail("row empirical event counts do not form one partition")
    lower_sum = sum(
        (item.lower_probability for item in row.intervals),
        Fraction(0),
    )
    upper_sum = sum(
        (item.upper_probability for item in row.intervals),
        Fraction(0),
    )
    if not lower_sum <= 1 <= upper_sum:
        _fail("row probability intervals have an empty simplex intersection")


@dataclass(frozen=True, slots=True)
class V075LearnedStateNodeV1:
    catalogue: public_graph.V075LegalActionCatalogueV1
    rows: tuple[backend.V075StatisticalRowV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.catalogue)
            is not public_graph.V075LegalActionCatalogueV1
            or type(self.rows) is not tuple
            or not self.rows
            or tuple(item.action for item in self.rows)
            != self.catalogue.actions
        ):
            _fail("learned state node lacks its complete ordered action rows")
        if any(
            item.context_id != self.catalogue.context_id
            or item.source_state_id != self.catalogue.state.state_id
            or item.remaining_horizon != self.catalogue.remaining_horizon
            for item in self.rows
        ):
            _fail("learned state node rows are stale or state-transplanted")
        for row in self.rows:
            try:
                binding = public_graph.observation_row_binding_v1(
                    self.catalogue.context,
                    self.catalogue,
                    row.action,
                )
            except (
                public_graph.V075PublicGraphSemanticsInvariantViolation
            ) as error:
                raise V075LearnedSupportPlannerInvariantViolation(
                    str(error)
                ) from error
            if binding.row_binding_id != row.row_binding_id:
                _fail("learned row binding ID does not replay from typed graph")
            _validate_intervals(row)
            for descriptor in row.support:
                _structural_successor(
                    context=self.catalogue.context,
                    source=self.catalogue.state,
                    action=row.action,
                    descriptor=descriptor,
                    remaining_horizon=self.catalogue.remaining_horizon,
                )

    @property
    def state_id(self) -> str:
        return self.catalogue.state.state_id

    @property
    def remaining_horizon(self) -> int:
        return self.catalogue.remaining_horizon

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_learned_support_state_node.v1",
            "schema_version": SCHEMA_VERSION,
            "context_id": self.catalogue.context_id,
            "state_id": self.state_id,
            "remaining_horizon": self.remaining_horizon,
            "catalogue_id": self.catalogue.catalogue_id,
            "row_ids": [item.row_id for item in self.rows],
            "complete_public_action_catalogue": True,
            "transition_law_access": False,
        }

    @property
    def node_id(self) -> str:
        return _hash("state_node", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "catalogue": self.catalogue.to_document(),
            "rows": [item.to_document() for item in self.rows],
            "node_id": self.node_id,
        }


@dataclass(frozen=True, slots=True)
class V075LearnedSupportGraphV1:
    backend_result: backend.V075RouteNativeBackendResultV1
    context: public_authority.V075PublicReplicateContextV1
    nodes: tuple[V075LearnedStateNodeV1, ...]
    observation_artifact_ref_ids: tuple[str, ...]
    familywise_confidence_error_upper: Fraction

    def __post_init__(self) -> None:
        if (
            type(self.backend_result)
            is not backend.V075RouteNativeBackendResultV1
            or type(self.context)
            is not public_authority.V075PublicReplicateContextV1
            or self.backend_result.model.occurrence_id
            != self.backend_result.occurrence_id
        ):
            _fail("learned support graph backend/context binding is malformed")
        if (
            self.context.context_id
            != _registered_context(self.context.context_id).context_id
            or type(self.nodes) is not tuple
            or not self.nodes
            or tuple(item.node_id for item in self.nodes)
            != tuple(sorted({item.node_id for item in self.nodes}))
            or self.observation_artifact_ref_ids
            != tuple(sorted(set(self.observation_artifact_ref_ids)))
            or type(self.familywise_confidence_error_upper) is not Fraction
            or not 0 < self.familywise_confidence_error_upper < 1
        ):
            _fail("learned support graph is noncanonical")
        for item in self.observation_artifact_ref_ids:
            _cid(item, "learned graph observation artifact")
        if any(
            node.catalogue.context != self.context for node in self.nodes
        ):
            _fail("learned support nodes were transplanted across contexts")
        root = public_graph.root_catalogue_v1(self.context)
        root_nodes = tuple(
            item
            for item in self.nodes
            if item.catalogue == root
        )
        if len(root_nodes) != 1:
            _fail("learned support graph requires exactly one typed root")
        node_states = {item.state_id: item for item in self.nodes}
        observed_positive_children = {
            descriptor.next_state_id
            for row in root_nodes[0].rows
            for descriptor in row.support
            if not descriptor.failure and not descriptor.terminal
        }
        actual_children = {
            item.state_id
            for item in self.nodes
            if item.remaining_horizon == 1
        }
        if not actual_children <= observed_positive_children:
            _fail(
                "learned support graph contains an unobserved or transplanted "
                "H=1 child"
            )
        if any(
            node_states[state_id].catalogue.state.failure
            for state_id in actual_children
        ):
            _fail("failure states cannot become decision nodes")
        model_rows = tuple(
            sorted(
                (item.row_id for item in self.backend_result.model.rows)
            )
        )
        graph_rows = tuple(
            sorted(item.row_id for node in self.nodes for item in node.rows)
        )
        if model_rows != graph_rows:
            _fail("learned support graph omitted or invented backend rows")
        expected_observations = tuple(
            sorted(
                {
                    capability_id
                    for row in self.backend_result.model.rows
                    for capability_id in (
                        *row.discovery_capability_ids,
                        *row.validation_capability_ids,
                    )
                }
            )
        )
        if (
            self.observation_artifact_ref_ids != expected_observations
            or tuple(
                sorted(self.backend_result.total_lift_input.capability_ref_ids)
            )
            != expected_observations
        ):
            _fail("learned support graph observation lineage is incomplete")

    @property
    def root(self) -> V075LearnedStateNodeV1:
        root_catalogue = public_graph.root_catalogue_v1(self.context)
        return next(
            item for item in self.nodes if item.catalogue == root_catalogue
        )

    @property
    def arm(self) -> worker.V075WorkerArmV1:
        return self.backend_result.arm

    @property
    def active_child_state_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(
                item.state_id
                for item in self.nodes
                if item.remaining_horizon == 1
            )
        )

    @property
    def complete_modeled_h2_closure(self) -> bool:
        observed = {
            descriptor.next_state_id
            for row in self.root.rows
            for descriptor in row.support
            if not descriptor.failure and not descriptor.terminal
        }
        return observed == set(self.active_child_state_ids)

    @property
    def row_active_support_descriptor_ids(
        self,
    ) -> tuple[tuple[str, tuple[str, ...]], ...]:
        active = set(self.active_child_state_ids)
        return tuple(
            (
                row.row_id,
                tuple(
                    descriptor.descriptor_id
                    for descriptor in row.support
                    if (
                        row.remaining_horizon == 1
                        or descriptor.failure
                        or descriptor.terminal
                        or descriptor.next_state_id in active
                    )
                ),
            )
            for node in sorted(self.nodes, key=lambda item: item.node_id)
            for row in node.rows
        )

    @property
    def unmaterialized_root_support_descriptor_ids(self) -> tuple[str, ...]:
        active = set(self.active_child_state_ids)
        return tuple(
            sorted(
                descriptor.descriptor_id
                for row in self.root.rows
                for descriptor in row.support
                if (
                    not descriptor.failure
                    and not descriptor.terminal
                    and descriptor.next_state_id not in active
                )
            )
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_learned_support_graph.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "backend_result_id": self.backend_result.result_id,
            "backend_model_id": self.backend_result.model.model_id,
            "request_id": self.backend_result.request_id,
            "occurrence_id": self.backend_result.occurrence_id,
            "arm": self.arm.value,
            "context_id": self.context.context_id,
            "root_node_id": self.root.node_id,
            "node_ids": [item.node_id for item in self.nodes],
            "observation_artifact_ref_ids": list(
                self.observation_artifact_ref_ids
            ),
            "familywise_confidence_error_upper": _fdoc(
                self.familywise_confidence_error_upper
            ),
            "active_child_state_ids": list(self.active_child_state_ids),
            "row_active_support_descriptor_ids": [
                {
                    "row_id": row_id,
                    "active_support_descriptor_ids": list(descriptor_ids),
                }
                for row_id, descriptor_ids
                in self.row_active_support_descriptor_ids
            ],
            "unmaterialized_root_support_descriptor_ids": list(
                self.unmaterialized_root_support_descriptor_ids
            ),
            "complete_modeled_h2_closure": (
                self.complete_modeled_h2_closure
            ),
            "partial_observed_world_model_allowed": True,
            "complete_root_action_catalogue": True,
            "complete_materialized_child_action_catalogues": True,
            "unmaterialized_positive_root_support_behavior": (
                "POLICY_ABORT_OTHER"
            ),
            "support_is_observation_driven": True,
            "other_behavior": POLICY_ABORT_RULE,
            "law_or_exact_atom_access": False,
            "may_certify_without_total_lift": False,
        }

    @property
    def graph_id(self) -> str:
        return _hash("support_graph", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "nodes": [item.to_document() for item in self.nodes],
            "graph_id": self.graph_id,
        }


def compile_v075_learned_support_graph_v1(
    claimed: backend.V075RouteNativeBackendResultV1,
) -> V075LearnedSupportGraphV1:
    """Reconstruct the observed partial H=2 world model."""

    if type(claimed) is not backend.V075RouteNativeBackendResultV1:
        _fail("learned support compiler rejects duck-typed backend results")
    if (
        claimed.schedule.status
        is not backend.V075BackendScheduleStatusV1
        .COMPLETE_REGISTERED_CHECKPOINT
        or not claimed.model.has_validation
        or not claimed.model.action_catalogues_complete
    ):
        _fail(
            "learned support compiler requires a complete registered "
            "validation checkpoint and action catalogues"
        )
    context = _registered_context(
        claimed.model.rows[0].context_id
    )
    if any(row.context_id != context.context_id for row in claimed.model.rows):
        _fail("backend model mixes replicate contexts")
    root = public_graph.root_catalogue_v1(context)
    observed_children: dict[
        str,
        public_graph.V075SymbolicGraphStateV1,
    ] = {}
    for row in claimed.model.rows:
        if row.remaining_horizon == 2:
            if row.source_state_id != root.state.state_id:
                _fail("H=2 backend row is not rooted at the public root")
            for descriptor in row.support:
                successor = _structural_successor(
                    context=context,
                    source=root.state,
                    action=row.action,
                    descriptor=descriptor,
                    remaining_horizon=2,
                )
                if not descriptor.failure and not descriptor.terminal:
                    observed_children[successor.state_id] = successor
    rows_by_state: dict[str, list[backend.V075StatisticalRowV1]] = {}
    for row in claimed.model.rows:
        rows_by_state.setdefault(row.source_state_id, []).append(row)
    actual_child_state_ids = {
        row.source_state_id
        for row in claimed.model.rows
        if row.remaining_horizon == 1
    }
    if (
        any(
            row.remaining_horizon != (
                2 if row.source_state_id == root.state.state_id else 1
            )
            for row in claimed.model.rows
        )
        or not actual_child_state_ids <= set(observed_children)
    ):
        _fail(
            "materialized child rows are horizon-drifted, unobserved, or "
            "state-transplanted"
        )
    states: dict[str, public_graph.V075SymbolicGraphStateV1] = {
        root.state.state_id: root.state,
        **{
            state_id: observed_children[state_id]
            for state_id in actual_child_state_ids
        },
    }
    nodes: list[V075LearnedStateNodeV1] = []
    for state_id, state in sorted(states.items()):
        horizon = 2 if state_id == root.state.state_id else 1
        catalogue = (
            root
            if horizon == 2
            else public_graph.V075LegalActionCatalogueV1(
                context,
                state,
                1,
                public_graph.legal_action_triples_v1(
                    context,
                    state.ranks,
                    state.failure,
                ),
            )
        )
        by_action = {
            row.action: row for row in rows_by_state.get(state_id, ())
        }
        if set(by_action) != set(catalogue.actions):
            _fail(
                "backend rows do not cover one complete materialized "
                "reconstructed catalogue"
            )
        nodes.append(
            V075LearnedStateNodeV1(
                catalogue,
                tuple(by_action[action] for action in catalogue.actions),
            )
        )
    canonical_nodes = tuple(sorted(nodes, key=lambda item: item.node_id))
    observations = tuple(
        sorted(
            {
                capability_id
                for row in claimed.model.rows
                for capability_id in (
                    *row.discovery_capability_ids,
                    *row.validation_capability_ids,
                )
            }
        )
    )
    validated_row_count = len(claimed.model.rows)
    return V075LearnedSupportGraphV1(
        claimed,
        context,
        canonical_nodes,
        observations,
        backend.ROW_EPOCH_BETA * validated_row_count,
    )


class V075RobustDestinationKindV1(str, Enum):
    CHILD_CELL = "CHILD_CELL"
    ENVIRONMENT_FAILURE = "ENVIRONMENT_FAILURE"
    SAFE_HORIZON_END = "SAFE_HORIZON_END"
    POLICY_ABORT_OTHER = "POLICY_ABORT_OTHER"


@dataclass(frozen=True, slots=True)
class V075RobustEventTermV1:
    destination_kind: V075RobustDestinationKindV1
    destination_id: str | None
    immediate_reward: Fraction
    lower_probability: Fraction
    upper_probability: Fraction

    def __post_init__(self) -> None:
        if type(self.destination_kind) is not V075RobustDestinationKindV1:
            _fail("robust event destination is not typed")
        if self.destination_kind is V075RobustDestinationKindV1.CHILD_CELL:
            if self.destination_id is None:
                _fail("child event lacks its quotient cell")
            _cid(self.destination_id, "robust event child cell")
        elif self.destination_id is not None:
            _fail("terminal or OTHER event cannot carry a child cell")
        if (
            type(self.immediate_reward) is not Fraction
            or self.immediate_reward < 0
            or type(self.lower_probability) is not Fraction
            or type(self.upper_probability) is not Fraction
            or not 0
            <= self.lower_probability
            <= self.upper_probability
            <= 1
        ):
            _fail("robust event reward or probability interval is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "destination_kind": self.destination_kind.value,
            "destination_id": self.destination_id,
            "immediate_reward": _fdoc(self.immediate_reward),
            "lower_probability": _fdoc(self.lower_probability),
            "upper_probability": _fdoc(self.upper_probability),
        }


@dataclass(frozen=True, slots=True)
class V075RowBehaviorBindingV1:
    row_id: str
    remaining_horizon: int
    terms: tuple[V075RobustEventTermV1, ...]

    def __post_init__(self) -> None:
        _cid(self.row_id, "row behavior source row")
        if (
            self.remaining_horizon not in (1, 2)
            or type(self.terms) is not tuple
            or not self.terms
            or any(type(item) is not V075RobustEventTermV1 for item in self.terms)
            or tuple(canonical_json_bytes(item.to_document()) for item in self.terms)
            != tuple(
                sorted(
                    canonical_json_bytes(item.to_document())
                    for item in self.terms
                )
            )
        ):
            _fail("row behavior terms are empty, untyped, or noncanonical")
        if (
            sum(
                (item.lower_probability for item in self.terms),
                Fraction(0),
            )
            > 1
            or sum(
                (item.upper_probability for item in self.terms),
                Fraction(0),
            )
            < 1
            or sum(
                item.destination_kind
                is V075RobustDestinationKindV1.POLICY_ABORT_OTHER
                for item in self.terms
            )
            != 1
        ):
            _fail("row behavior interval simplex or OTHER partition is invalid")

    def _behavior_payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_learned_row_behavior.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "terms": [item.to_document() for item in self.terms],
            "other_behavior": POLICY_ABORT_RULE,
            "interval_simplex_retained": True,
        }

    @property
    def behavior_key(self) -> str:
        return _hash("row_behavior", self._behavior_payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._behavior_payload(),
            "row_id": self.row_id,
            "behavior_key": self.behavior_key,
        }


@dataclass(frozen=True, slots=True)
class V075QuotientCellV1:
    remaining_horizon: int
    state_node_ids: tuple[str, ...]
    state_ids: tuple[str, ...]
    semantic_keys: tuple[str, ...]

    def __post_init__(self) -> None:
        if (
            self.remaining_horizon not in (1, 2)
            or self.state_node_ids
            != tuple(sorted(set(self.state_node_ids)))
            or self.state_ids != tuple(sorted(set(self.state_ids)))
            or not self.state_ids
            or len(self.state_node_ids) != len(self.state_ids)
            or self.semantic_keys != tuple(sorted(set(self.semantic_keys)))
            or not self.semantic_keys
        ):
            _fail("quotient cell members or semantic keys are noncanonical")
        for value in (*self.state_node_ids, *self.state_ids, *self.semantic_keys):
            _cid(value, "quotient cell member")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observation_driven_quotient_cell.v1",
            "schema_version": SCHEMA_VERSION,
            "remaining_horizon": self.remaining_horizon,
            "state_node_ids": list(self.state_node_ids),
            "state_ids": list(self.state_ids),
            "semantic_keys": list(self.semantic_keys),
            "partition_basis": (
                "OBSERVED_INTERVAL_BEHAVIORAL_BISIMULATION_SIGNATURE"
            ),
        }

    @property
    def cell_id(self) -> str:
        return _hash("cell", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "cell_id": self.cell_id}


@dataclass(frozen=True, slots=True)
class V075DistinctActionConcretizerV1:
    cell_id: str
    state_id: str
    semantic_key: str
    ground_actions: tuple[tuple[int, int, int], ...]
    row_ids: tuple[str, ...]
    uniform_weights: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        for value, name in (
            (self.cell_id, "concretizer cell"),
            (self.state_id, "concretizer state"),
            (self.semantic_key, "concretizer semantic key"),
        ):
            _cid(value, name)
        if (
            type(self.ground_actions) is not tuple
            or not self.ground_actions
            or self.ground_actions != tuple(sorted(set(self.ground_actions)))
            or len(set(self.row_ids)) != len(self.row_ids)
            or len(self.row_ids) != len(self.ground_actions)
            or type(self.uniform_weights) is not tuple
            or len(self.uniform_weights) != len(self.ground_actions)
            or any(
                type(item) is not Fraction
                or item != Fraction(1, len(self.ground_actions))
                for item in self.uniform_weights
            )
            or sum(self.uniform_weights, Fraction(0)) != 1
        ):
            _fail(
                "concretizer must be uniform over complete distinct actions"
            )
        for action in self.ground_actions:
            _action(action, "concretizer ground action")
        for row_id in self.row_ids:
            _cid(row_id, "concretizer row")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": (
                "acfqp.v075_observation_driven_distinct_action_"
                "concretizer.v1"
            ),
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell_id,
            "state_id": self.state_id,
            "semantic_key": self.semantic_key,
            "ground_actions": [list(item) for item in self.ground_actions],
            "row_ids": list(self.row_ids),
            "action_row_bindings": [
                {"ground_action": list(action), "row_id": row_id}
                for action, row_id in zip(self.ground_actions, self.row_ids)
            ],
            "uniform_weights": [_fdoc(item) for item in self.uniform_weights],
            "distinct_actions_deduplicated_before_weighting": True,
            "policy_randomization": False,
        }

    @property
    def concretizer_id(self) -> str:
        return _hash("concretizer", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "concretizer_id": self.concretizer_id}


@dataclass(frozen=True, slots=True)
class V075CompiledSemanticActionV1:
    cell: V075QuotientCellV1
    semantic_key: str
    concretizers: tuple[V075DistinctActionConcretizerV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.cell) is not V075QuotientCellV1
            or self.semantic_key not in self.cell.semantic_keys
            or self.concretizers
            != tuple(
                sorted(
                    self.concretizers,
                    key=lambda item: item.state_id,
                )
            )
            or tuple(item.state_id for item in self.concretizers)
            != self.cell.state_ids
            or any(
                type(item) is not V075DistinctActionConcretizerV1
                or item.cell_id != self.cell.cell_id
                or item.semantic_key != self.semantic_key
                for item in self.concretizers
            )
        ):
            _fail("compiled semantic action is incomplete or transplanted")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observation_driven_semantic_action.v1",
            "schema_version": SCHEMA_VERSION,
            "cell_id": self.cell.cell_id,
            "remaining_horizon": self.cell.remaining_horizon,
            "semantic_key": self.semantic_key,
            "concretizer_ids": [
                item.concretizer_id for item in self.concretizers
            ],
            "deterministic_semantic_selector_compatible": True,
        }

    @property
    def semantic_action_id(self) -> str:
        return _hash("semantic_action", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "concretizers": [
                item.to_document() for item in self.concretizers
            ],
            "semantic_action_id": self.semantic_action_id,
        }


@dataclass(frozen=True, slots=True)
class V075ObservationDrivenQuotientV1:
    graph: V075LearnedSupportGraphV1
    row_behaviors: tuple[V075RowBehaviorBindingV1, ...]
    cells: tuple[V075QuotientCellV1, ...]
    semantic_actions: tuple[V075CompiledSemanticActionV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.graph) is not V075LearnedSupportGraphV1
            or self.graph.arm
            is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
            or self.row_behaviors
            != tuple(sorted(self.row_behaviors, key=lambda item: item.row_id))
            or self.cells
            != tuple(sorted(self.cells, key=lambda item: item.cell_id))
            or self.semantic_actions
            != tuple(
                sorted(
                    self.semantic_actions,
                    key=lambda item: item.semantic_action_id,
                )
            )
        ):
            _fail("observation-driven quotient is malformed or direct-routed")
        expected_rows = tuple(
            sorted(
                row.row_id
                for node in self.graph.nodes
                for row in node.rows
            )
        )
        if tuple(item.row_id for item in self.row_behaviors) != expected_rows:
            _fail("quotient row behavior registry is incomplete")
        cell_states = tuple(
            sorted(state_id for cell in self.cells for state_id in cell.state_ids)
        )
        if cell_states != tuple(
            sorted(node.state_id for node in self.graph.nodes)
        ):
            _fail("quotient cells do not partition the learned states")
        expected_action_pairs = {
            (cell.cell_id, semantic_key)
            for cell in self.cells
            for semantic_key in cell.semantic_keys
        }
        actual_action_pairs = {
            (item.cell.cell_id, item.semantic_key)
            for item in self.semantic_actions
        }
        if expected_action_pairs != actual_action_pairs:
            _fail("quotient semantic action registry is incomplete")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_observation_driven_quotient.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "learned_support_graph_id": self.graph.graph_id,
            "row_behavior_bindings": [
                {
                    "row_id": item.row_id,
                    "behavior_key": item.behavior_key,
                }
                for item in self.row_behaviors
            ],
            "cell_ids": [item.cell_id for item in self.cells],
            "semantic_action_ids": [
                item.semantic_action_id for item in self.semantic_actions
            ],
            "compiler": (
                "BOTTOM_UP_H2_INTERVAL_BEHAVIORAL_BISIMULATION_V1"
            ),
            "initial_human_or_group_partition_used": False,
            "known_automorphism_used": False,
            "fixed_uniform_distinct_action_concretizer": True,
            "law_or_exact_atom_access": False,
        }

    @property
    def quotient_id(self) -> str:
        return _hash("quotient", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "row_behaviors": [
                item.to_document() for item in self.row_behaviors
            ],
            "cells": [item.to_document() for item in self.cells],
            "semantic_actions": [
                item.to_document() for item in self.semantic_actions
            ],
            "quotient_id": self.quotient_id,
        }

    def cell_for_state(self, state_id: str) -> V075QuotientCellV1:
        _cid(state_id, "quotient state lookup")
        result = tuple(
            item for item in self.cells if state_id in item.state_ids
        )
        if len(result) != 1:
            _fail("quotient state is absent or multiply assigned")
        return result[0]

    def actions_for_cell(
        self,
        cell_id: str,
    ) -> tuple[V075CompiledSemanticActionV1, ...]:
        _cid(cell_id, "quotient action cell")
        return tuple(
            item
            for item in self.semantic_actions
            if item.cell.cell_id == cell_id
        )


def _aggregate_terms(
    values: Iterable[V075RobustEventTermV1],
) -> tuple[V075RobustEventTermV1, ...]:
    totals: dict[
        tuple[V075RobustDestinationKindV1, str | None, Fraction],
        tuple[Fraction, Fraction],
    ] = {}
    for item in values:
        key = (
            item.destination_kind,
            item.destination_id,
            item.immediate_reward,
        )
        lower, upper = totals.get(key, (Fraction(0), Fraction(0)))
        totals[key] = (
            lower + item.lower_probability,
            upper + item.upper_probability,
        )
    result = tuple(
        V075RobustEventTermV1(
            key[0],
            key[1],
            key[2],
            lower,
            min(Fraction(1), upper),
        )
        for key, (lower, upper) in totals.items()
    )
    return tuple(
        sorted(result, key=lambda item: canonical_json_bytes(item.to_document()))
    )


def _row_behavior(
    row: backend.V075StatisticalRowV1,
    *,
    child_cell_by_state: Mapping[str, str],
) -> V075RowBehaviorBindingV1:
    interval_by_key = {item.event_key: item for item in row.intervals}
    terms: list[V075RobustEventTermV1] = []
    for descriptor in row.support:
        interval = interval_by_key[descriptor.descriptor_id]
        if descriptor.failure:
            kind = V075RobustDestinationKindV1.ENVIRONMENT_FAILURE
            destination_id = None
        elif row.remaining_horizon == 1:
            kind = V075RobustDestinationKindV1.SAFE_HORIZON_END
            destination_id = None
        elif descriptor.next_state_id not in child_cell_by_state:
            kind = V075RobustDestinationKindV1.POLICY_ABORT_OTHER
            destination_id = None
        else:
            kind = V075RobustDestinationKindV1.CHILD_CELL
            destination_id = child_cell_by_state[descriptor.next_state_id]
        terms.append(
            V075RobustEventTermV1(
                kind,
                destination_id,
                descriptor.realized_row_reward,
                interval.lower_probability,
                interval.upper_probability,
            )
        )
    other = interval_by_key["OTHER"]
    immediate_rewards = {
        item.realized_row_reward for item in row.support
    }
    if len(immediate_rewards) != 1:
        _fail("one learned row has outcome-dependent merge rewards")
    terms.append(
        V075RobustEventTermV1(
            V075RobustDestinationKindV1.POLICY_ABORT_OTHER,
            None,
            next(iter(immediate_rewards)),
            other.lower_probability,
            other.upper_probability,
        )
    )
    return V075RowBehaviorBindingV1(
        row.row_id,
        row.remaining_horizon,
        _aggregate_terms(terms),
    )


def _compile_level(
    nodes: tuple[V075LearnedStateNodeV1, ...],
    behaviors: Mapping[str, V075RowBehaviorBindingV1],
) -> tuple[
    tuple[V075QuotientCellV1, ...],
    tuple[V075CompiledSemanticActionV1, ...],
]:
    groups_by_state: dict[
        str,
        dict[str, list[backend.V075StatisticalRowV1]],
    ] = {}
    signatures: dict[tuple[int, tuple[str, ...]], list[V075LearnedStateNodeV1]] = {}
    for node in nodes:
        groups: dict[str, list[backend.V075StatisticalRowV1]] = {}
        for row in node.rows:
            groups.setdefault(behaviors[row.row_id].behavior_key, []).append(row)
        groups_by_state[node.state_id] = groups
        signature = (
            node.remaining_horizon,
            tuple(sorted(groups)),
        )
        signatures.setdefault(signature, []).append(node)
    cells: list[V075QuotientCellV1] = []
    actions: list[V075CompiledSemanticActionV1] = []
    for signature in sorted(signatures):
        members = tuple(
            sorted(signatures[signature], key=lambda item: item.state_id)
        )
        cell = V075QuotientCellV1(
            signature[0],
            tuple(sorted(item.node_id for item in members)),
            tuple(item.state_id for item in members),
            signature[1],
        )
        cells.append(cell)
        for semantic_key in signature[1]:
            concretizers: list[V075DistinctActionConcretizerV1] = []
            for node in members:
                rows = tuple(
                    sorted(
                        groups_by_state[node.state_id][semantic_key],
                        key=lambda item: item.action,
                    )
                )
                concretizers.append(
                    V075DistinctActionConcretizerV1(
                        cell.cell_id,
                        node.state_id,
                        semantic_key,
                        tuple(item.action for item in rows),
                        tuple(item.row_id for item in rows),
                        tuple(
                            Fraction(1, len(rows)) for _item in rows
                        ),
                    )
                )
            actions.append(
                V075CompiledSemanticActionV1(
                    cell,
                    semantic_key,
                    tuple(
                        sorted(
                            concretizers,
                            key=lambda item: item.state_id,
                        )
                    ),
                )
            )
    return (
        tuple(sorted(cells, key=lambda item: item.cell_id)),
        tuple(sorted(actions, key=lambda item: item.semantic_action_id)),
    )


def compile_v075_observation_driven_quotient_v1(
    graph: V075LearnedSupportGraphV1,
) -> V075ObservationDrivenQuotientV1:
    """Compile the coarsest bottom-up H=2 behavioral partition."""

    if type(graph) is not V075LearnedSupportGraphV1:
        _fail("quotient compiler rejects duck-typed learned graphs")
    if graph.arm is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        _fail("matched direct arm must not pass through the quotient compiler")
    child_nodes = tuple(
        item for item in graph.nodes if item.remaining_horizon == 1
    )
    child_behaviors = {
        row.row_id: _row_behavior(row, child_cell_by_state={})
        for node in child_nodes
        for row in node.rows
    }
    child_cells, child_actions = _compile_level(
        child_nodes,
        child_behaviors,
    )
    child_cell_by_state = {
        state_id: cell.cell_id
        for cell in child_cells
        for state_id in cell.state_ids
    }
    root_nodes = tuple(
        item for item in graph.nodes if item.remaining_horizon == 2
    )
    root_behaviors = {
        row.row_id: _row_behavior(
            row,
            child_cell_by_state=child_cell_by_state,
        )
        for node in root_nodes
        for row in node.rows
    }
    root_cells, root_actions = _compile_level(
        root_nodes,
        root_behaviors,
    )
    behaviors = tuple(
        sorted(
            (*child_behaviors.values(), *root_behaviors.values()),
            key=lambda item: item.row_id,
        )
    )
    return V075ObservationDrivenQuotientV1(
        graph,
        behaviors,
        tuple(
            sorted(
                (*child_cells, *root_cells),
                key=lambda item: item.cell_id,
            )
        ),
        tuple(
            sorted(
                (*child_actions, *root_actions),
                key=lambda item: item.semantic_action_id,
            )
        ),
    )


class V075PlannerRouteV1(str, Enum):
    ADAPTIVE_QUOTIENT = "ADAPTIVE_QUOTIENT"
    MATCHED_DIRECT_GROUND = "MATCHED_DIRECT_GROUND"


class V075PlannerStatusV1(str, Enum):
    CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT = (
        "CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT"
    )
    STATISTICAL_ENVELOPE_NOT_CERTIFIED = (
        "STATISTICAL_ENVELOPE_NOT_CERTIFIED"
    )
    NO_RISK_FEASIBLE_POLICY = "NO_RISK_FEASIBLE_POLICY"
    SEARCH_CAP_EXHAUSTED = "SEARCH_CAP_EXHAUSTED"


@dataclass(frozen=True, slots=True)
class V075PolicyStateChoiceV1:
    state_id: str
    ground_actions: tuple[tuple[int, int, int], ...]
    row_ids: tuple[str, ...]
    uniform_weights: tuple[Fraction, ...]

    def __post_init__(self) -> None:
        _cid(self.state_id, "policy state choice")
        if (
            type(self.ground_actions) is not tuple
            or not self.ground_actions
            or self.ground_actions != tuple(sorted(set(self.ground_actions)))
            or len(set(self.row_ids)) != len(self.row_ids)
            or len(self.row_ids) != len(self.ground_actions)
            or type(self.uniform_weights) is not tuple
            or len(self.uniform_weights) != len(self.ground_actions)
            or any(
                type(item) is not Fraction
                or item != Fraction(1, len(self.ground_actions))
                for item in self.uniform_weights
            )
        ):
            _fail("policy state choice is not one complete fixed concretizer")
        for item in self.ground_actions:
            _action(item, "policy state choice action")
        for item in self.row_ids:
            _cid(item, "policy state choice row")

    def to_document(self) -> dict[str, Any]:
        return {
            "state_id": self.state_id,
            "ground_actions": [list(item) for item in self.ground_actions],
            "row_ids": list(self.row_ids),
            "action_row_bindings": [
                {"ground_action": list(action), "row_id": row_id}
                for action, row_id in zip(self.ground_actions, self.row_ids)
            ],
            "uniform_weights": [_fdoc(item) for item in self.uniform_weights],
        }


@dataclass(frozen=True, slots=True)
class V075DeterministicPolicyDecisionV1:
    route: V075PlannerRouteV1
    remaining_horizon: int
    decision_domain_id: str
    selected_option_id: str
    state_choices: tuple[V075PolicyStateChoiceV1, ...]

    def __post_init__(self) -> None:
        if (
            type(self.route) is not V075PlannerRouteV1
            or self.remaining_horizon not in (1, 2)
            or type(self.state_choices) is not tuple
            or not self.state_choices
            or self.state_choices
            != tuple(sorted(self.state_choices, key=lambda item: item.state_id))
            or len({item.state_id for item in self.state_choices})
            != len(self.state_choices)
        ):
            _fail("deterministic policy decision is malformed")
        _cid(self.decision_domain_id, "policy decision domain")
        _cid(self.selected_option_id, "policy selected option")
        if (
            self.route is V075PlannerRouteV1.MATCHED_DIRECT_GROUND
            and (
                len(self.state_choices) != 1
                or len(self.state_choices[0].ground_actions) != 1
                or self.state_choices[0].state_id != self.decision_domain_id
            )
        ):
            _fail("direct decision must select exactly one ground action")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_robust_h2_policy_decision.v1",
            "schema_version": SCHEMA_VERSION,
            "route": self.route.value,
            "remaining_horizon": self.remaining_horizon,
            "decision_domain_id": self.decision_domain_id,
            "selected_option_id": self.selected_option_id,
            "state_choices": [
                item.to_document() for item in self.state_choices
            ],
            "deterministic_selector": True,
            "fixed_concretizer": True,
        }

    @property
    def decision_id(self) -> str:
        return _hash("decision", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "decision_id": self.decision_id}


@dataclass(frozen=True, slots=True)
class V075DeterministicH2PolicyV1:
    learned_support_graph_id: str
    route: V075PlannerRouteV1
    quotient_id: str | None
    decisions: tuple[V075DeterministicPolicyDecisionV1, ...]

    def __post_init__(self) -> None:
        _cid(self.learned_support_graph_id, "policy learned support graph")
        if type(self.route) is not V075PlannerRouteV1:
            _fail("policy route is not typed")
        if self.route is V075PlannerRouteV1.ADAPTIVE_QUOTIENT:
            if self.quotient_id is None:
                _fail("abstract policy lacks its quotient")
            _cid(self.quotient_id, "abstract policy quotient")
        elif self.quotient_id is not None:
            _fail("matched direct policy cannot claim a quotient")
        if (
            type(self.decisions) is not tuple
            or not self.decisions
            or self.decisions
            != tuple(
                sorted(
                    self.decisions,
                    key=lambda item: (
                        -item.remaining_horizon,
                        item.decision_domain_id,
                    ),
                )
            )
            or sum(item.remaining_horizon == 2 for item in self.decisions) != 1
            or any(item.route is not self.route for item in self.decisions)
        ):
            _fail("H=2 policy decision registry is noncanonical")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_robust_h2_deterministic_policy.v1",
            "schema_version": SCHEMA_VERSION,
            "learned_support_graph_id": self.learned_support_graph_id,
            "route": self.route.value,
            "quotient_id": self.quotient_id,
            "decision_ids": [item.decision_id for item in self.decisions],
            "deterministic_finite_horizon_markov_selector": True,
            "fixed_stochastic_concretizer_is_not_policy_randomization": True,
        }

    @property
    def policy_id(self) -> str:
        return _hash("policy", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "decisions": [item.to_document() for item in self.decisions],
            "policy_id": self.policy_id,
        }


@dataclass(frozen=True, slots=True)
class V075RobustH2EnvelopeV1:
    policy: V075DeterministicH2PolicyV1
    selected_reward_lower: Fraction
    selected_reward_upper: Fraction
    unrestricted_reward_upper: Fraction
    selected_failure_upper: Fraction
    normalized_regret_upper: Fraction
    familywise_confidence_error_upper: Fraction

    def __post_init__(self) -> None:
        if type(self.policy) is not V075DeterministicH2PolicyV1:
            _fail("robust envelope lacks its typed policy")
        values = (
            self.selected_reward_lower,
            self.selected_reward_upper,
            self.unrestricted_reward_upper,
            self.selected_failure_upper,
            self.normalized_regret_upper,
            self.familywise_confidence_error_upper,
        )
        if any(type(item) is not Fraction for item in values):
            _fail("robust envelope must use exact rational arithmetic")
        if (
            not 0
            <= self.selected_reward_lower
            <= self.selected_reward_upper
            <= self.unrestricted_reward_upper
            or not 0 <= self.selected_failure_upper <= 1
            or self.normalized_regret_upper < 0
            or not 0 < self.familywise_confidence_error_upper < 1
        ):
            _fail("robust envelope bounds are malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_robust_h2_operational_envelope.v1",
            "schema_version": SCHEMA_VERSION,
            "policy_id": self.policy.policy_id,
            "selected_reward_lower": _fdoc(self.selected_reward_lower),
            "selected_reward_upper": _fdoc(self.selected_reward_upper),
            "unrestricted_reward_upper": _fdoc(
                self.unrestricted_reward_upper
            ),
            "selected_failure_upper": _fdoc(self.selected_failure_upper),
            "normalized_regret_upper": _fdoc(
                self.normalized_regret_upper
            ),
            "familywise_confidence_error_upper": _fdoc(
                self.familywise_confidence_error_upper
            ),
            "probability_simplex_enforced": True,
            "other_behavior": POLICY_ABORT_RULE,
            "law_or_exact_atom_access": False,
        }

    @property
    def envelope_id(self) -> str:
        return _hash("envelope", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "envelope_id": self.envelope_id}


PLANNER_COUNTER_PATHS = (
    "common.learned_support_graph_checks",
    "common.interval_row_evaluations",
    "common.interval_lp_allocations",
    "common.policy_assignments_evaluated",
    "common.dominance_comparisons",
    "common.deterministic_tie_breaks",
    "adaptive.quotient_compiler_calls",
    "adaptive.cells_compiled",
    "adaptive.semantic_actions_compiled",
    "adaptive.concretizer_ground_actions",
    "adaptive.planner_calls",
    "direct.planner_calls",
    "direct.ground_states_considered",
    "direct.ground_actions_considered",
    "common.total_lift_candidate_emissions",
)


@dataclass(frozen=True, slots=True)
class V075SupportPlannerCounterV1:
    path: str
    value: int
    observed: bool = True

    def __post_init__(self) -> None:
        if (
            self.path not in PLANNER_COUNTER_PATHS
            or type(self.value) is not int
            or self.value < 0
            or self.observed is not True
        ):
            _fail("support planner counter is unknown or malformed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_support_planner_counter.v1",
            "schema_version": SCHEMA_VERSION,
            "path": self.path,
            "value": self.value,
            "observed": True,
            "lane": "OPERATIONAL_CONSTRUCTION",
        }

    @property
    def counter_id(self) -> str:
        return _hash("counter", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "counter_id": self.counter_id}


@dataclass(frozen=True, slots=True)
class V075SupportPlannerWorkV1:
    learned_support_graph_id: str
    route: V075PlannerRouteV1
    counters: tuple[V075SupportPlannerCounterV1, ...]

    def __post_init__(self) -> None:
        _cid(self.learned_support_graph_id, "planner work support graph")
        if (
            type(self.route) is not V075PlannerRouteV1
            or type(self.counters) is not tuple
            or tuple(item.path for item in self.counters)
            != PLANNER_COUNTER_PATHS
        ):
            _fail("planner work counters are incomplete or reordered")
        values = {item.path: item.value for item in self.counters}
        adaptive = self.route is V075PlannerRouteV1.ADAPTIVE_QUOTIENT
        if (
            values["adaptive.planner_calls"] != int(adaptive)
            or values["direct.planner_calls"] != int(not adaptive)
            or (
                adaptive
                and (
                    values["direct.ground_states_considered"] != 0
                    or values["direct.ground_actions_considered"] != 0
                )
            )
            or (
                not adaptive
                and (
                    values["adaptive.quotient_compiler_calls"] != 0
                    or values["adaptive.cells_compiled"] != 0
                    or values["adaptive.semantic_actions_compiled"] != 0
                    or values["adaptive.concretizer_ground_actions"] != 0
                )
            )
        ):
            _fail("adaptive and direct planner work lanes are mixed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_support_planner_work.v1",
            "schema_version": SCHEMA_VERSION,
            "learned_support_graph_id": self.learned_support_graph_id,
            "route": self.route.value,
            "counter_ids": [item.counter_id for item in self.counters],
            "required_counter_paths": list(PLANNER_COUNTER_PATHS),
            "native_zeros_complete": True,
            "route_lanes_disjoint": True,
        }

    @property
    def work_id(self) -> str:
        return _hash("work", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "counters": [item.to_document() for item in self.counters],
            "work_id": self.work_id,
        }


@dataclass(frozen=True, slots=True)
class V075SupportPlannerResultV1:
    graph: V075LearnedSupportGraphV1
    route: V075PlannerRouteV1
    quotient: V075ObservationDrivenQuotientV1 | None
    status: V075PlannerStatusV1
    policy: V075DeterministicH2PolicyV1 | None
    envelope: V075RobustH2EnvelopeV1 | None
    diagnostic_failed_frontier_row_ids: tuple[str, ...]
    work: V075SupportPlannerWorkV1
    search_cap: int

    def __post_init__(self) -> None:
        if (
            type(self.graph) is not V075LearnedSupportGraphV1
            or type(self.route) is not V075PlannerRouteV1
            or type(self.status) is not V075PlannerStatusV1
            or type(self.work) is not V075SupportPlannerWorkV1
            or type(self.diagnostic_failed_frontier_row_ids) is not tuple
            or len(set(self.diagnostic_failed_frontier_row_ids))
            != len(self.diagnostic_failed_frontier_row_ids)
            or self.work.learned_support_graph_id != self.graph.graph_id
            or self.work.route is not self.route
            or type(self.search_cap) is not int
            or self.search_cap != MAX_EXACT_POLICY_ASSIGNMENTS
        ):
            _fail("support planner result is malformed")
        if self.route is V075PlannerRouteV1.ADAPTIVE_QUOTIENT:
            if (
                type(self.quotient) is not V075ObservationDrivenQuotientV1
                or self.quotient.graph != self.graph
            ):
                _fail("abstract planner result lacks its typed quotient")
        elif self.quotient is not None:
            _fail("matched direct planner result illegally claims a quotient")
        has_policy = self.policy is not None and self.envelope is not None
        if has_policy:
            if (
                type(self.policy) is not V075DeterministicH2PolicyV1
                or type(self.envelope) is not V075RobustH2EnvelopeV1
                or self.envelope.policy != self.policy
                or self.policy.route is not self.route
            ):
                _fail("planner policy/envelope identity graph is inconsistent")
        elif self.policy is not None or self.envelope is not None:
            _fail("planner cannot emit a partial policy/envelope pair")
        policy_statuses = {
            V075PlannerStatusV1.CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT,
            V075PlannerStatusV1.STATISTICAL_ENVELOPE_NOT_CERTIFIED,
            V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY,
        }
        if (self.status in policy_statuses) != has_policy:
            _fail("planner status disagrees with policy availability")
        diagnostic = (
            self.status is V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        )
        if diagnostic:
            assert self.policy is not None and self.envelope is not None
            root_rows = {
                row_id
                for decision in self.policy.decisions
                if decision.remaining_horizon == 2
                for choice in decision.state_choices
                for row_id in choice.row_ids
            }
            child_rows = {
                row_id
                for decision in self.policy.decisions
                if decision.remaining_horizon == 1
                for choice in decision.state_choices
                for row_id in choice.row_ids
            }
            expected_frontier = (
                *sorted(root_rows),
                *sorted(child_rows - root_rows),
            )
            if (
                not self.diagnostic_failed_frontier_row_ids
                or self.diagnostic_failed_frontier_row_ids
                != expected_frontier
                or self.envelope.selected_failure_upper
                <= worker.V075WorkerThresholdProfileV1().risk_tolerance
            ):
                _fail(
                    "NO_RISK_FEASIBLE lacks its exact failed diagnostic "
                    "policy frontier"
                )
        elif self.diagnostic_failed_frontier_row_ids:
            _fail("non-diagnostic planner result claims a failed frontier")

    @property
    def ready_for_exact_total_lift(self) -> bool:
        return (
            self.status
            is V075PlannerStatusV1.CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_support_planner_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "learned_support_graph_id": self.graph.graph_id,
            "route": self.route.value,
            "quotient_id": (
                None if self.quotient is None else self.quotient.quotient_id
            ),
            "status": self.status.value,
            "policy_id": None if self.policy is None else self.policy.policy_id,
            "envelope_id": (
                None if self.envelope is None else self.envelope.envelope_id
            ),
            "diagnostic_failed_frontier_row_ids": list(
                self.diagnostic_failed_frontier_row_ids
            ),
            "diagnostic_selection_rule": (
                (
                    "MIN_FAILURE_UPPER_THEN_MAX_REWARD_LOWER_THEN_"
                    "LEXICOGRAPHIC_POLICY_V1"
                )
                if self.status
                is V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
                else None
            ),
            "work_id": self.work.work_id,
            "search_cap": self.search_cap,
            "ready_for_exact_total_lift": self.ready_for_exact_total_lift,
            "artifact_scope": "OPERATIONAL_INTERMEDIATE_CANDIDATE",
            "scientific_plan_certificate": False,
            "production_integration_ready": False,
            "law_or_exact_atom_access": False,
        }

    @property
    def result_id(self) -> str:
        return _hash("result", self._payload())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "quotient": (
                None if self.quotient is None else self.quotient.to_document()
            ),
            "policy": None if self.policy is None else self.policy.to_document(),
            "envelope": (
                None if self.envelope is None else self.envelope.to_document()
            ),
            "work": self.work.to_document(),
            "result_id": self.result_id,
        }

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


@dataclass(frozen=True, slots=True)
class _MetricV1:
    reward_lower: Fraction
    reward_upper: Fraction
    failure_upper: Fraction


@dataclass(frozen=True, slots=True)
class _OptionV1:
    option_id: str
    domain_id: str
    remaining_horizon: int
    rows_by_state: tuple[
        tuple[str, tuple[backend.V075StatisticalRowV1, ...]],
        ...,
    ]


@dataclass(slots=True)
class _WorkTallyV1:
    row_evaluations: int = 0
    lp_allocations: int = 0
    policy_assignments: int = 0
    dominance_comparisons: int = 0
    tie_breaks: int = 0


def _extreme_expectation(
    terms: tuple[V075RobustEventTermV1, ...],
    values: tuple[Fraction, ...],
    *,
    maximize: bool,
    tally: _WorkTallyV1,
) -> Fraction:
    if (
        len(terms) != len(values)
        or not terms
        or any(type(item) is not Fraction for item in values)
    ):
        _fail("interval LP objective is malformed")
    lower = [item.lower_probability for item in terms]
    upper = [item.upper_probability for item in terms]
    residual = Fraction(1) - sum(lower, Fraction(0))
    if residual < 0 or sum(upper, Fraction(0)) < 1:
        _fail("interval LP feasible simplex is empty")
    order = sorted(
        range(len(terms)),
        key=lambda index: (
            values[index],
            canonical_json_bytes(terms[index].to_document()),
        ),
        reverse=maximize,
    )
    probabilities = list(lower)
    for index in order:
        addition = min(residual, upper[index] - lower[index])
        probabilities[index] += addition
        residual -= addition
        tally.lp_allocations += 1
        if residual == 0:
            break
    if residual != 0 or sum(probabilities, Fraction(0)) != 1:
        _fail("interval LP greedy extreme failed exact simplex closure")
    return sum(
        (
            probability * value
            for probability, value in zip(probabilities, values)
        ),
        Fraction(0),
    )


def _evaluate_behavior(
    behavior: V075RowBehaviorBindingV1,
    *,
    child_reward_lower: Mapping[str, Fraction],
    child_reward_upper: Mapping[str, Fraction],
    child_failure_upper: Mapping[str, Fraction],
    tally: _WorkTallyV1,
) -> _MetricV1:
    reward_lower_values: list[Fraction] = []
    reward_upper_values: list[Fraction] = []
    failure_values: list[Fraction] = []
    for term in behavior.terms:
        if term.destination_kind is V075RobustDestinationKindV1.CHILD_CELL:
            assert term.destination_id is not None
            try:
                continuation_lower = child_reward_lower[term.destination_id]
                continuation_upper = child_reward_upper[term.destination_id]
                continuation_failure = child_failure_upper[
                    term.destination_id
                ]
            except KeyError as error:
                raise V075LearnedSupportPlannerInvariantViolation(
                    "policy lacks a modeled child continuation"
                ) from error
        elif term.destination_kind in {
            V075RobustDestinationKindV1.ENVIRONMENT_FAILURE,
            V075RobustDestinationKindV1.POLICY_ABORT_OTHER,
        }:
            continuation_lower = Fraction(0)
            continuation_upper = Fraction(0)
            continuation_failure = Fraction(1)
        else:
            continuation_lower = Fraction(0)
            continuation_upper = Fraction(0)
            continuation_failure = Fraction(0)
        reward_lower_values.append(
            term.immediate_reward + continuation_lower
        )
        reward_upper_values.append(
            term.immediate_reward + continuation_upper
        )
        failure_values.append(continuation_failure)
    tally.row_evaluations += 1
    return _MetricV1(
        _extreme_expectation(
            behavior.terms,
            tuple(reward_lower_values),
            maximize=False,
            tally=tally,
        ),
        _extreme_expectation(
            behavior.terms,
            tuple(reward_upper_values),
            maximize=True,
            tally=tally,
        ),
        _extreme_expectation(
            behavior.terms,
            tuple(failure_values),
            maximize=True,
            tally=tally,
        ),
    )


def _node_map(
    graph: V075LearnedSupportGraphV1,
) -> dict[str, V075LearnedStateNodeV1]:
    return {item.state_id: item for item in graph.nodes}


def _adaptive_options(
    quotient: V075ObservationDrivenQuotientV1,
    *,
    remaining_horizon: int,
) -> tuple[_OptionV1, ...]:
    behavior_by_row = {
        item.row_id: item for item in quotient.row_behaviors
    }
    nodes = _node_map(quotient.graph)
    result: list[_OptionV1] = []
    for semantic in quotient.semantic_actions:
        if semantic.cell.remaining_horizon != remaining_horizon:
            continue
        rows_by_state: list[
            tuple[str, tuple[backend.V075StatisticalRowV1, ...]]
        ] = []
        for concretizer in semantic.concretizers:
            node = nodes[concretizer.state_id]
            rows = tuple(
                sorted(
                    (
                        row
                        for row in node.rows
                        if behavior_by_row[row.row_id].behavior_key
                        == semantic.semantic_key
                    ),
                    key=lambda item: item.action,
                )
            )
            if (
                tuple(item.action for item in rows)
                != concretizer.ground_actions
                or tuple(item.row_id for item in rows)
                != concretizer.row_ids
            ):
                _fail("semantic action concretizer differs from row registry")
            rows_by_state.append((concretizer.state_id, rows))
        result.append(
            _OptionV1(
                semantic.semantic_action_id,
                semantic.cell.cell_id,
                remaining_horizon,
                tuple(rows_by_state),
            )
        )
    return tuple(sorted(result, key=lambda item: item.option_id))


def _direct_behaviors(
    graph: V075LearnedSupportGraphV1,
) -> tuple[V075RowBehaviorBindingV1, ...]:
    child_identity = {
        node.state_id: node.state_id
        for node in graph.nodes
        if node.remaining_horizon == 1
    }
    return tuple(
        sorted(
            (
                _row_behavior(
                    row,
                    child_cell_by_state=child_identity,
                )
                for node in graph.nodes
                for row in node.rows
            ),
            key=lambda item: item.row_id,
        )
    )


def _direct_options(
    graph: V075LearnedSupportGraphV1,
    *,
    remaining_horizon: int,
) -> tuple[_OptionV1, ...]:
    return tuple(
        sorted(
            (
                _OptionV1(
                    row.row_id,
                    node.state_id,
                    remaining_horizon,
                    ((node.state_id, (row,)),),
                )
                for node in graph.nodes
                if node.remaining_horizon == remaining_horizon
                for row in node.rows
            ),
            key=lambda item: item.option_id,
        )
    )


def _option_metric(
    option: _OptionV1,
    *,
    behavior_by_row: Mapping[str, V075RowBehaviorBindingV1],
    child_reward_lower: Mapping[str, Fraction],
    child_reward_upper: Mapping[str, Fraction],
    child_failure_upper: Mapping[str, Fraction],
    tally: _WorkTallyV1,
) -> _MetricV1:
    metrics = tuple(
        _evaluate_behavior(
            behavior_by_row[row.row_id],
            child_reward_lower=child_reward_lower,
            child_reward_upper=child_reward_upper,
            child_failure_upper=child_failure_upper,
            tally=tally,
        )
        for _state_id, rows in option.rows_by_state
        for row in rows
    )
    if not metrics or any(item != metrics[0] for item in metrics[1:]):
        _fail(
            "one semantic action does not have representative-independent "
            "interval behavior"
        )
    return metrics[0]


def _pareto_options(
    options: tuple[_OptionV1, ...],
    metrics: Mapping[str, _MetricV1],
    tally: _WorkTallyV1,
) -> tuple[_OptionV1, ...]:
    retained: list[_OptionV1] = []
    for candidate in options:
        candidate_metric = metrics[candidate.option_id]
        dominated = False
        for other in options:
            if other.option_id == candidate.option_id:
                continue
            tally.dominance_comparisons += 1
            other_metric = metrics[other.option_id]
            if (
                other_metric.reward_lower >= candidate_metric.reward_lower
                and other_metric.failure_upper
                <= candidate_metric.failure_upper
                and (
                    other_metric.reward_lower > candidate_metric.reward_lower
                    or other_metric.failure_upper
                    < candidate_metric.failure_upper
                    or (
                        other_metric == candidate_metric
                        and other.option_id < candidate.option_id
                    )
                )
            ):
                dominated = True
                if other_metric == candidate_metric:
                    tally.tie_breaks += 1
                break
        if not dominated:
            retained.append(candidate)
    return tuple(sorted(retained, key=lambda item: item.option_id))


def _decision_from_option(
    option: _OptionV1,
    route: V075PlannerRouteV1,
) -> V075DeterministicPolicyDecisionV1:
    choices = tuple(
        V075PolicyStateChoiceV1(
            state_id,
            tuple(row.action for row in rows),
            tuple(row.row_id for row in rows),
            tuple(Fraction(1, len(rows)) for _row in rows),
        )
        for state_id, rows in option.rows_by_state
    )
    return V075DeterministicPolicyDecisionV1(
        route,
        option.remaining_horizon,
        option.domain_id,
        option.option_id,
        tuple(sorted(choices, key=lambda item: item.state_id)),
    )


def _planner_work(
    *,
    graph: V075LearnedSupportGraphV1,
    route: V075PlannerRouteV1,
    quotient: V075ObservationDrivenQuotientV1 | None,
    tally: _WorkTallyV1,
    emitted: bool,
) -> V075SupportPlannerWorkV1:
    adaptive = route is V075PlannerRouteV1.ADAPTIVE_QUOTIENT
    values = {
        "common.learned_support_graph_checks": 1,
        "common.interval_row_evaluations": tally.row_evaluations,
        "common.interval_lp_allocations": tally.lp_allocations,
        "common.policy_assignments_evaluated": tally.policy_assignments,
        "common.dominance_comparisons": tally.dominance_comparisons,
        "common.deterministic_tie_breaks": tally.tie_breaks,
        "adaptive.quotient_compiler_calls": int(adaptive),
        "adaptive.cells_compiled": (
            len(quotient.cells) if quotient is not None else 0
        ),
        "adaptive.semantic_actions_compiled": (
            len(quotient.semantic_actions) if quotient is not None else 0
        ),
        "adaptive.concretizer_ground_actions": (
            sum(
                len(concretizer.ground_actions)
                for semantic in quotient.semantic_actions
                for concretizer in semantic.concretizers
            )
            if quotient is not None
            else 0
        ),
        "adaptive.planner_calls": int(adaptive),
        "direct.planner_calls": int(not adaptive),
        "direct.ground_states_considered": (
            0 if adaptive else len(graph.nodes)
        ),
        "direct.ground_actions_considered": (
            0
            if adaptive
            else sum(len(item.rows) for item in graph.nodes)
        ),
        "common.total_lift_candidate_emissions": int(emitted),
    }
    return V075SupportPlannerWorkV1(
        graph.graph_id,
        route,
        tuple(
            V075SupportPlannerCounterV1(path, values[path])
            for path in PLANNER_COUNTER_PATHS
        ),
    )


def _solve(
    *,
    graph: V075LearnedSupportGraphV1,
    route: V075PlannerRouteV1,
    quotient: V075ObservationDrivenQuotientV1 | None,
    behaviors: tuple[V075RowBehaviorBindingV1, ...],
    root_options: tuple[_OptionV1, ...],
    child_options: tuple[_OptionV1, ...],
) -> V075SupportPlannerResultV1:
    behavior_by_row = {item.row_id: item for item in behaviors}
    if (
        tuple(sorted(behavior_by_row))
        != tuple(
            sorted(row.row_id for node in graph.nodes for row in node.rows)
        )
        or not root_options
    ):
        _fail("planner behavior or root option registry is incomplete")
    tally = _WorkTallyV1()
    child_metrics: dict[str, _MetricV1] = {
        option.option_id: _option_metric(
            option,
            behavior_by_row=behavior_by_row,
            child_reward_lower={},
            child_reward_upper={},
            child_failure_upper={},
            tally=tally,
        )
        for option in child_options
    }
    children_by_domain: dict[str, list[_OptionV1]] = {}
    for option in child_options:
        children_by_domain.setdefault(option.domain_id, []).append(option)
    pareto_by_domain = {
        domain_id: _pareto_options(
            tuple(options),
            child_metrics,
            tally,
        )
        for domain_id, options in children_by_domain.items()
    }
    # Unrestricted reward upper is a sound upper on the constrained optimum.
    upper_choice_by_domain: dict[str, _OptionV1] = {}
    for domain_id, options in children_by_domain.items():
        ordered = sorted(
            options,
            key=lambda item: (
                -child_metrics[item.option_id].reward_upper,
                item.option_id,
            ),
        )
        if (
            len(ordered) > 1
            and child_metrics[ordered[0].option_id].reward_upper
            == child_metrics[ordered[1].option_id].reward_upper
        ):
            tally.tie_breaks += 1
        upper_choice_by_domain[domain_id] = ordered[0]
    unrestricted_reward_upper = Fraction(0)
    for root_option in root_options:
        upper_metric = _option_metric(
            root_option,
            behavior_by_row=behavior_by_row,
            child_reward_lower={
                domain_id: child_metrics[option.option_id].reward_lower
                for domain_id, option in upper_choice_by_domain.items()
            },
            child_reward_upper={
                domain_id: child_metrics[option.option_id].reward_upper
                for domain_id, option in upper_choice_by_domain.items()
            },
            child_failure_upper={
                domain_id: child_metrics[option.option_id].failure_upper
                for domain_id, option in upper_choice_by_domain.items()
            },
            tally=tally,
        )
        if upper_metric.reward_upper > unrestricted_reward_upper:
            unrestricted_reward_upper = upper_metric.reward_upper
    threshold = worker.V075WorkerThresholdProfileV1()
    best: tuple[
        Fraction,
        Fraction,
        str,
        tuple[tuple[str, str], ...],
        _OptionV1,
        dict[str, _OptionV1],
        _MetricV1,
    ] | None = None
    diagnostic_best: tuple[
        Fraction,
        Fraction,
        str,
        tuple[tuple[str, str], ...],
        _OptionV1,
        dict[str, _OptionV1],
        _MetricV1,
    ] | None = None
    exhausted = False
    for root_option in root_options:
        relevant_domains = tuple(
            sorted(
                {
                    term.destination_id
                    for _state_id, rows in root_option.rows_by_state
                    for row in rows
                    for term in behavior_by_row[row.row_id].terms
                    if term.destination_kind
                    is V075RobustDestinationKindV1.CHILD_CELL
                }
            )
        )
        if any(
            domain_id not in pareto_by_domain for domain_id in relevant_domains
        ):
            _fail("root option lacks one modeled child decision domain")
        products: Iterable[tuple[_OptionV1, ...]]
        if relevant_domains:
            products = itertools.product(
                *(pareto_by_domain[item] for item in relevant_domains)
            )
        else:
            products = ((),)
        for combination in products:
            tally.policy_assignments += 1
            if tally.policy_assignments > MAX_EXACT_POLICY_ASSIGNMENTS:
                exhausted = True
                break
            assignment = dict(zip(relevant_domains, combination))
            metric = _option_metric(
                root_option,
                behavior_by_row=behavior_by_row,
                child_reward_lower={
                    domain_id: child_metrics[option.option_id].reward_lower
                    for domain_id, option in assignment.items()
                },
                child_reward_upper={
                    domain_id: child_metrics[option.option_id].reward_upper
                    for domain_id, option in assignment.items()
                },
                child_failure_upper={
                    domain_id: child_metrics[option.option_id].failure_upper
                    for domain_id, option in assignment.items()
                },
                tally=tally,
            )
            assignment_key = tuple(
                (domain_id, assignment[domain_id].option_id)
                for domain_id in relevant_domains
            )
            candidate = (
                metric.reward_lower,
                metric.failure_upper,
                root_option.option_id,
                assignment_key,
                root_option,
                assignment,
                metric,
            )
            if (
                diagnostic_best is None
                or candidate[1] < diagnostic_best[1]
                or (
                    candidate[1] == diagnostic_best[1]
                    and (
                        candidate[0] > diagnostic_best[0]
                        or (
                            candidate[0] == diagnostic_best[0]
                            and (candidate[2], candidate[3])
                            < (
                                diagnostic_best[2],
                                diagnostic_best[3],
                            )
                        )
                    )
                )
            ):
                if (
                    diagnostic_best is not None
                    and candidate[:2] == diagnostic_best[:2]
                ):
                    tally.tie_breaks += 1
                diagnostic_best = candidate
            elif (
                diagnostic_best is not None
                and candidate[:2] == diagnostic_best[:2]
            ):
                tally.tie_breaks += 1
            if metric.failure_upper > threshold.risk_tolerance:
                continue
            if best is None:
                best = candidate
                continue
            if (
                candidate[0] > best[0]
                or (
                    candidate[0] == best[0]
                    and (
                        candidate[1] < best[1]
                        or (
                            candidate[1] == best[1]
                            and (candidate[2], candidate[3])
                            < (best[2], best[3])
                        )
                    )
                )
            ):
                if candidate[:2] == best[:2]:
                    tally.tie_breaks += 1
                best = candidate
            elif candidate[:2] == best[:2]:
                tally.tie_breaks += 1
        if exhausted:
            break
    if exhausted:
        work = _planner_work(
            graph=graph,
            route=route,
            quotient=quotient,
            tally=tally,
            emitted=False,
        )
        return V075SupportPlannerResultV1(
            graph,
            route,
            quotient,
            V075PlannerStatusV1.SEARCH_CAP_EXHAUSTED,
            None,
            None,
            (),
            work,
            MAX_EXACT_POLICY_ASSIGNMENTS,
        )
    diagnostic = best is None
    if diagnostic:
        if diagnostic_best is None:
            _fail("complete exact search produced no diagnostic policy")
        best = diagnostic_best
    root_option = best[4]
    assignment = best[5]
    selected_metric = best[6]
    decisions = (
        _decision_from_option(root_option, route),
        *(
            _decision_from_option(assignment[domain_id], route)
            for domain_id in sorted(assignment)
        ),
    )
    policy = V075DeterministicH2PolicyV1(
        graph.graph_id,
        route,
        None if quotient is None else quotient.quotient_id,
        tuple(
            sorted(
                decisions,
                key=lambda item: (
                    -item.remaining_horizon,
                    item.decision_domain_id,
                ),
            )
        ),
    )
    if unrestricted_reward_upper < selected_metric.reward_upper:
        _fail("unrestricted reward upper is below the selected policy upper")
    normalized_regret = (
        unrestricted_reward_upper - selected_metric.reward_lower
    ) / threshold.reward_ceiling
    envelope = V075RobustH2EnvelopeV1(
        policy,
        selected_metric.reward_lower,
        selected_metric.reward_upper,
        unrestricted_reward_upper,
        selected_metric.failure_upper,
        normalized_regret,
        graph.familywise_confidence_error_upper,
    )
    status = (
        V075PlannerStatusV1.NO_RISK_FEASIBLE_POLICY
        if diagnostic
        else (
            V075PlannerStatusV1.CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
            if normalized_regret <= threshold.normalized_regret_tolerance
            else V075PlannerStatusV1.STATISTICAL_ENVELOPE_NOT_CERTIFIED
        )
    )
    emitted = (
        status
        is V075PlannerStatusV1.CANDIDATE_CERTIFIED_FOR_EXACT_TOTAL_LIFT
    )
    work = _planner_work(
        graph=graph,
        route=route,
        quotient=quotient,
        tally=tally,
        emitted=emitted,
    )
    diagnostic_frontier = ()
    if diagnostic:
        root_rows = tuple(
            sorted(
                {
                    row.row_id
                    for _state_id, rows in root_option.rows_by_state
                    for row in rows
                }
            )
        )
        child_rows = tuple(
            sorted(
                {
                    row.row_id
                    for option in assignment.values()
                    for _state_id, rows in option.rows_by_state
                    for row in rows
                }
                - set(root_rows)
            )
        )
        diagnostic_frontier = (*root_rows, *child_rows)
    return V075SupportPlannerResultV1(
        graph,
        route,
        quotient,
        status,
        policy,
        envelope,
        diagnostic_frontier,
        work,
        MAX_EXACT_POLICY_ASSIGNMENTS,
    )


def plan_v075_exact_h2_abstract_v1(
    graph: V075LearnedSupportGraphV1,
) -> V075SupportPlannerResultV1:
    """Compile and solve the adaptive quotient interval model exactly."""

    quotient = compile_v075_observation_driven_quotient_v1(graph)
    return _solve(
        graph=graph,
        route=V075PlannerRouteV1.ADAPTIVE_QUOTIENT,
        quotient=quotient,
        behaviors=quotient.row_behaviors,
        root_options=_adaptive_options(quotient, remaining_horizon=2),
        child_options=_adaptive_options(quotient, remaining_horizon=1),
    )


def plan_v075_exact_h2_matched_direct_ground_v1(
    graph: V075LearnedSupportGraphV1,
) -> V075SupportPlannerResultV1:
    """Solve the matched non-quotiented interval model exactly."""

    if type(graph) is not V075LearnedSupportGraphV1:
        _fail("direct planner rejects duck-typed learned graphs")
    if graph.arm is not worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND:
        _fail("matched direct planner requires the registered direct arm")
    return _solve(
        graph=graph,
        route=V075PlannerRouteV1.MATCHED_DIRECT_GROUND,
        quotient=None,
        behaviors=_direct_behaviors(graph),
        root_options=_direct_options(graph, remaining_horizon=2),
        child_options=_direct_options(graph, remaining_horizon=1),
    )


def verify_v075_abstract_planner_result_v1(
    *,
    graph: V075LearnedSupportGraphV1,
    claimed_bytes: bytes,
) -> V075SupportPlannerResultV1:
    expected = plan_v075_exact_h2_abstract_v1(graph)
    if type(claimed_bytes) is not bytes or claimed_bytes != expected.canonical_bytes:
        _fail("abstract planner result differs from exact recomputation")
    return expected


def verify_v075_matched_direct_planner_result_v1(
    *,
    graph: V075LearnedSupportGraphV1,
    claimed_bytes: bytes,
) -> V075SupportPlannerResultV1:
    expected = plan_v075_exact_h2_matched_direct_ground_v1(graph)
    if type(claimed_bytes) is not bytes or claimed_bytes != expected.canonical_bytes:
        _fail("matched direct planner result differs from exact recomputation")
    return expected


__all__ = [
    "DOMAIN_TAGS",
    "MAX_EXACT_POLICY_ASSIGNMENTS",
    "PLANNER_COUNTER_PATHS",
    "POLICY_ABORT_RULE",
    "PRODUCTION_INTEGRATION_READY",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SCIENTIFIC_CERTIFICATE_ISSUANCE_ALLOWED",
    "V075CompiledSemanticActionV1",
    "V075DeterministicH2PolicyV1",
    "V075DeterministicPolicyDecisionV1",
    "V075DistinctActionConcretizerV1",
    "V075LearnedStateNodeV1",
    "V075LearnedSupportGraphV1",
    "V075LearnedSupportPlannerInvariantViolation",
    "V075ObservationDrivenQuotientV1",
    "V075PlannerRouteV1",
    "V075PlannerStatusV1",
    "V075PolicyStateChoiceV1",
    "V075QuotientCellV1",
    "V075RobustDestinationKindV1",
    "V075RobustEventTermV1",
    "V075RobustH2EnvelopeV1",
    "V075RowBehaviorBindingV1",
    "V075SupportPlannerCounterV1",
    "V075SupportPlannerResultV1",
    "V075SupportPlannerWorkV1",
    "compile_v075_learned_support_graph_v1",
    "compile_v075_observation_driven_quotient_v1",
    "plan_v075_exact_h2_abstract_v1",
    "plan_v075_exact_h2_matched_direct_ground_v1",
    "verify_v075_abstract_planner_result_v1",
    "verify_v075_matched_direct_planner_result_v1",
]
