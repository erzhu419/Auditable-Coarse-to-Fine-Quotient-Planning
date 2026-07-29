"""Strict child-to-parent transport for already computed V0-075 planning.

The child serializes three canonical public documents: the batch-native
backend result, its learned-support graph, and its planner result.  The parent
reconstructs the existing exact dataclass graph from those documents and the
typed signed batches.  This module deliberately has no model compiler,
confidence builder, planner, solver, or search fallback.

The loaded ``backend_result`` and ``planner_result`` can be passed directly to
the existing batch-native total-lift lineage authority.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from fractions import Fraction
import hashlib
from typing import Any, Mapping, TypeVar

from acfqp.phase3e_ids import (
    Phase3EIdentityError,
    canonical_json_bytes,
    loads_canonical_json,
    parse_content_id,
)
from acfqp import v075_batch_native_statistical_backend_v1 as batch_backend
from acfqp import v075_batched_observer_authority_v1 as batched
from acfqp import v075_learned_support_quotient_planners_v1 as planners
from acfqp import v075_public_graph_semantics_v1 as graph
from acfqp import v075_registered_occurrence_worker_v1 as worker
from acfqp import v075_route_native_backend_core_v1 as route_backend


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "1.42.0"
PROFILE_KEY = "v075_operational_planner_transport_v1"

MODEL_COMPILATION_ALLOWED = False
PLANNER_EXECUTION_ALLOWED = False
SOLVER_OR_SEARCH_ALLOWED = False
PRIVATE_MATERIAL_ALLOWED = False
PER_DRAW_CAPABILITY_EXPANSION_ALLOWED = False

DOMAIN_TAGS = {
    "transport": "acfqp:v075-operational-planner-transport:v1",
    "load": "acfqp:v075-operational-planner-load:v1",
}

if len(DOMAIN_TAGS) != len(set(DOMAIN_TAGS.values())):
    raise RuntimeError("V0-075 operational transport domains overlap")


class V075OperationalPlannerTransportInvariantViolation(ValueError):
    """One canonical transport or reconstructed identity graph was invalid."""


def _fail(message: str) -> None:
    raise V075OperationalPlannerTransportInvariantViolation(message)


def _hash(role: str, payload: Mapping[str, Any]) -> str:
    try:
        return hashlib.sha256(
            DOMAIN_TAGS[role].encode("utf-8")
            + b"\x00"
            + canonical_json_bytes(dict(payload))
        ).hexdigest()
    except (KeyError, TypeError, ValueError) as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            str(error)
        ) from error


def _cid(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            f"{field_name} must be one lowercase SHA-256 content ID"
        ) from error


def _mapping(value: Any, field_name: str) -> dict[str, Any]:
    if type(value) is not dict:
        _fail(f"{field_name} must be one exact JSON object")
    return value


def _list(value: Any, field_name: str) -> list[Any]:
    if type(value) is not list:
        _fail(f"{field_name} must be one exact JSON array")
    return value


def _tuple_strings(value: Any, field_name: str) -> tuple[str, ...]:
    values = _list(value, field_name)
    if any(type(item) is not str for item in values):
        _fail(f"{field_name} must contain only strings")
    return tuple(values)


def _action(value: Any, field_name: str) -> tuple[int, int, int]:
    values = _list(value, field_name)
    if (
        len(values) != 3
        or any(type(item) is not int for item in values)
    ):
        _fail(f"{field_name} must be one integer ground-action triple")
    return tuple(values)  # type: ignore[return-value]


def _fraction(value: Any, field_name: str) -> Fraction:
    if type(value) is Fraction:
        return value
    item = _mapping(value, field_name)
    if (
        set(item) != {"numerator", "denominator"}
        or type(item["numerator"]) is not int
        or type(item["denominator"]) is not int
        or item["denominator"] <= 0
    ):
        _fail(f"{field_name} must be one exact rational document")
    result = Fraction(item["numerator"], item["denominator"])
    if {
        "numerator": result.numerator,
        "denominator": result.denominator,
    } != item:
        _fail(f"{field_name} is not a reduced canonical rational")
    return result


E = TypeVar("E", bound=Enum)


def _enum(enum_type: type[E], value: Any, field_name: str) -> E:
    if type(value) is not str:
        _fail(f"{field_name} must be one enum string")
    try:
        return enum_type(value)
    except ValueError as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            f"{field_name} is not registered"
        ) from error


def _same(
    reconstructed: Mapping[str, Any],
    claimed: Mapping[str, Any],
    field_name: str,
) -> None:
    if canonical_json_bytes(dict(reconstructed)) != canonical_json_bytes(
        dict(claimed)
    ):
        _fail(
            f"{field_name} has missing, unknown, noncanonical, or "
            "identity-inconsistent fields"
        )


def _canonical_document(raw: bytes, field_name: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{field_name} must be nonempty canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except (Phase3EIdentityError, TypeError, ValueError) as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            f"{field_name} is not valid canonical JSON: {error}"
        ) from error
    item = _mapping(document, field_name)
    if canonical_json_bytes(item) != raw:
        _fail(f"{field_name} is not encoded canonically")
    return item


def _hex_bytes(value: Any, field_name: str) -> bytes:
    if type(value) is not str or not value:
        _fail(f"{field_name} must be nonempty hexadecimal bytes")
    try:
        result = bytes.fromhex(value)
    except ValueError as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            f"{field_name} is not hexadecimal"
        ) from error
    if result.hex() != value:
        _fail(f"{field_name} uses noncanonical hexadecimal")
    return result


def _load_schedule(
    document: Any,
) -> route_backend.V075RouteScheduleV1:
    item = _mapping(document, "route schedule")

    def counts(name: str) -> tuple[tuple[str, int], ...]:
        result = []
        for value in _list(item[name], f"route schedule {name}"):
            pair = _mapping(value, f"route schedule {name} member")
            if (
                set(pair) != {"stream_id", "draw_count"}
                or type(pair["stream_id"]) is not str
                or type(pair["draw_count"]) is not int
            ):
                _fail(f"route schedule {name} member is malformed")
            result.append((pair["stream_id"], pair["draw_count"]))
        return tuple(result)

    result = route_backend.V075RouteScheduleV1(
        item["request_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "schedule arm"),
        _enum(worker.V075WorkerRouteV1, item["route"], "schedule route"),
        counts("discovery_stream_counts"),
        counts("validation_stream_counts"),
        _enum(
            route_backend.V075BackendScheduleStatusV1,
            item["status"],
            "schedule status",
        ),
        item["cap_profile_id"],
    )
    _same(result.to_document(), item, "route schedule")
    return result


def _load_proposal(
    document: Any,
) -> route_backend.V075ProposalBasisV1:
    item = _mapping(document, "proposal basis")
    result = route_backend.V075ProposalBasisV1(
        item["request_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "proposal arm"),
        _enum(
            worker.V075WorkerProposalSemanticsV1,
            item["proposal_semantics"],
            "proposal semantics",
        ),
        tuple(
            _fraction(value, "proposal exact midrank")
            for value in _list(
                item["exact_midrank_vector"],
                "proposal exact midrank vector",
            )
        ),
        item["source_transport_id"],
    )
    _same(result.to_document(), item, "proposal basis")
    return result


def _load_descriptor(
    document: Any,
) -> route_backend.V075OutcomeDescriptorV1:
    item = _mapping(document, "outcome descriptor")
    ranks = _list(item["next_ranks"], "outcome ranks")
    if any(type(value) is not int for value in ranks):
        _fail("outcome ranks must contain only integers")
    result = route_backend.V075OutcomeDescriptorV1(
        item["context_id"],
        item["next_state_id"],
        tuple(ranks),
        item["failure"],
        item["terminal"],
        _fraction(item["realized_row_reward"], "outcome reward"),
    )
    _same(result.to_document(), item, "outcome descriptor")
    return result


def _load_interval(
    document: Any,
    descriptors: Mapping[str, route_backend.V075OutcomeDescriptorV1],
) -> route_backend.V075EventIntervalV1:
    item = _mapping(document, "event interval")
    descriptor_id = item["descriptor_id"]
    if descriptor_id is None:
        descriptor = None
    elif type(descriptor_id) is str and descriptor_id in descriptors:
        descriptor = descriptors[descriptor_id]
    else:
        _fail("event interval descriptor is absent or transplanted")
    result = route_backend.V075EventIntervalV1(
        item["event_key"],
        descriptor,
        item["draw_count"],
        item["success_count"],
        _fraction(
            item["empirical_probability"],
            "event empirical probability",
        ),
        _fraction(item["lower_probability"], "event lower probability"),
        _fraction(item["upper_probability"], "event upper probability"),
        item["exact_likelihood_comparisons"],
        item["log_search_evaluations"],
    )
    _same(result.to_document(), item, "event interval")
    return result


def _load_row(document: Any) -> route_backend.V075StatisticalRowV1:
    item = _mapping(document, "statistical row")
    support = tuple(
        _load_descriptor(value)
        for value in _list(item["support"], "statistical-row support")
    )
    descriptors = {value.descriptor_id: value for value in support}
    if len(descriptors) != len(support):
        _fail("statistical-row support duplicates a descriptor")
    intervals = tuple(
        _load_interval(value, descriptors)
        for value in _list(
            item["intervals"],
            "statistical-row intervals",
        )
    )
    result = route_backend.V075StatisticalRowV1(
        item["context_id"],
        item["row_binding_id"],
        item["source_state_id"],
        item["remaining_horizon"],
        _action(item["action"], "statistical-row action"),
        _tuple_strings(
            item["discovery_capability_ids"],
            "statistical-row discovery capabilities",
        ),
        _tuple_strings(
            item["validation_capability_ids"],
            "statistical-row validation capabilities",
        ),
        support,
        intervals,
        item["validation_epoch_index"],
        item["blocker"],
    )
    _same(result.to_document(), item, "statistical row")
    return result


def _load_model(
    document: Any,
) -> route_backend.V075StatisticalModelV1:
    item = _mapping(document, "statistical model")
    result = route_backend.V075StatisticalModelV1(
        item["request_id"],
        item["occurrence_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "model arm"),
        item["proposal_id"],
        item["schedule_id"],
        tuple(
            _load_row(value)
            for value in _list(item["rows"], "statistical-model rows")
        ),
        item["root_catalogue_complete"],
        item["modeled_child_catalogues_complete"],
        _tuple_strings(
            item["unresolved_source_state_ids"],
            "model unresolved source states",
        ),
    )
    _same(result.to_document(), item, "statistical model")
    return result


def _load_policy_candidate(
    document: Any,
) -> route_backend.V075PolicyCandidateV1:
    item = _mapping(document, "policy candidate")
    result = route_backend.V075PolicyCandidateV1(
        item["model_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "policy arm"),
        _enum(
            route_backend.V075BackendCandidateStatusV1,
            item["status"],
            "policy candidate status",
        ),
        _tuple_strings(
            item["candidate_root_row_ids"],
            "candidate root rows",
        ),
    )
    _same(result.to_document(), item, "policy candidate")
    return result


def _load_envelope_candidate(
    document: Any,
) -> route_backend.V075EnvelopeCandidateV1:
    item = _mapping(document, "envelope candidate")
    result = route_backend.V075EnvelopeCandidateV1(
        item["model_id"],
        item["policy_candidate_id"],
        _enum(
            route_backend.V075BackendCandidateStatusV1,
            item["status"],
            "envelope candidate status",
        ),
    )
    _same(result.to_document(), item, "envelope candidate")
    return result


def _load_total_lift_input(
    document: Any,
) -> route_backend.V075TotalLiftCandidateInputV1:
    item = _mapping(document, "total-lift candidate input")
    result = route_backend.V075TotalLiftCandidateInputV1(
        item["occurrence_id"],
        item["model_id"],
        item["policy_candidate_id"],
        item["envelope_candidate_id"],
        _enum(
            route_backend.V075BackendCandidateStatusV1,
            item["status"],
            "total-lift input status",
        ),
        _tuple_strings(item["observed_row_ids"], "observed row IDs"),
        _tuple_strings(
            item["capability_ref_ids"],
            "total-lift capability refs",
        ),
    )
    _same(result.to_document(), item, "total-lift candidate input")
    return result


def _load_route_work(
    document: Any,
) -> route_backend.V075BackendWorkV1:
    item = _mapping(document, "route-native work")
    counters = []
    for value in _list(item["counters"], "route-native counters"):
        counter = _mapping(value, "route-native counter")
        loaded = route_backend.V075BackendCounterV1(
            counter["path"],
            counter["value"],
            counter["observed"],
        )
        _same(loaded.to_document(), counter, "route-native counter")
        counters.append(loaded)
    result = route_backend.V075BackendWorkV1(
        item["request_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "route-work arm"),
        tuple(counters),
    )
    _same(result.to_document(), item, "route-native work")
    return result


def _load_route_result(
    document: Any,
) -> route_backend.V075RouteNativeBackendResultV1:
    item = _mapping(document, "route-native result")
    result = route_backend.V075RouteNativeBackendResultV1(
        item["request_id"],
        item["occurrence_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "route-result arm"),
        _load_schedule(item["schedule"]),
        _load_proposal(item["proposal"]),
        _load_model(item["model"]),
        _load_policy_candidate(item["policy"]),
        _load_envelope_candidate(item["envelope"]),
        _load_total_lift_input(item["total_lift_input"]),
        _load_route_work(item["work"]),
    )
    _same(result.to_document(), item, "route-native result")
    return result


def _load_batch_work(
    document: Any,
) -> batch_backend.V075BatchNativeWorkV1:
    item = _mapping(document, "batch-native work")
    counters = []
    for value in _list(item["counters"], "batch-native counters"):
        counter = _mapping(value, "batch-native counter")
        loaded = batch_backend.V075BatchNativeCounterV1(
            counter["path"],
            counter["value"],
            counter["observed"],
        )
        _same(loaded.to_document(), counter, "batch-native counter")
        counters.append(loaded)
    result = batch_backend.V075BatchNativeWorkV1(
        item["request_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "batch-work arm"),
        tuple(counters),
    )
    _same(result.to_document(), item, "batch-native work")
    return result


def _load_backend_result(
    document: Any,
    request: batch_backend.V075BatchNativeBackendRequestV1,
) -> batch_backend.V075BatchNativeBackendResultV1:
    item = _mapping(document, "batch-native backend result")
    _same(
        request.to_document(),
        _mapping(item["request"], "batch-native request document"),
        "batch-native request document",
    )
    result = batch_backend.V075BatchNativeBackendResultV1(
        request,
        _load_route_result(item["route_native_result"]),
        _tuple_strings(
            item["aggregate_support_evidence_ids"],
            "aggregate support evidence IDs",
        ),
        _tuple_strings(item["selected_batch_ids"], "selected batch IDs"),
        _tuple_strings(
            item["superseded_batch_ids"],
            "superseded batch IDs",
        ),
        _load_batch_work(item["work"]),
    )
    _same(
        result.to_document(),
        item,
        "batch-native backend result",
    )
    return result


def _graph_states(
    *,
    context: Any,
    backend_result: batch_backend.V075BatchNativeBackendResultV1,
) -> dict[str, graph.V075SymbolicGraphStateV1]:
    root = graph.root_catalogue_v1(context).state
    result = {root.state_id: root}
    for row in backend_result.route_native_result.model.rows:
        for descriptor in row.support:
            state = graph.V075SymbolicGraphStateV1(
                context,
                descriptor.next_ranks,
                descriptor.failure,
            )
            if state.state_id != descriptor.next_state_id:
                _fail("backend descriptor does not reconstruct its state")
            prior = result.get(state.state_id)
            if prior is not None and prior != state:
                _fail("one state ID has conflicting symbolic states")
            result[state.state_id] = state
    return result


def _load_graph(
    document: Any,
    backend_result: batch_backend.V075BatchNativeBackendResultV1,
) -> planners.V075LearnedSupportGraphV1:
    item = _mapping(document, "learned-support graph")
    context = backend_result.request.context
    states = _graph_states(
        context=context,
        backend_result=backend_result,
    )
    row_by_id = {
        row.row_id: row
        for row in backend_result.route_native_result.model.rows
    }
    nodes = []
    for value in _list(item["nodes"], "learned-support nodes"):
        node = _mapping(value, "learned-support node")
        state_id = node["state_id"]
        state = states.get(state_id)
        if state is None or state.failure:
            _fail("learned node state is absent, failed, or transplanted")
        horizon = node["remaining_horizon"]
        catalogue = (
            graph.root_catalogue_v1(context)
            if horizon == 2
            else graph.V075LegalActionCatalogueV1(
                context,
                state,
                horizon,
                graph.legal_action_triples_v1(
                    context,
                    state.ranks,
                    state.failure,
                ),
            )
        )
        rows = []
        for row_document in _list(node["rows"], "learned-node rows"):
            row_item = _mapping(row_document, "learned-node row")
            row = row_by_id.get(row_item["row_id"])
            if row is None:
                _fail("learned node references an absent backend row")
            _same(row.to_document(), row_item, "learned-node row")
            rows.append(row)
        loaded = planners.V075LearnedStateNodeV1(
            catalogue,
            tuple(rows),
        )
        _same(loaded.to_document(), node, "learned-support node")
        nodes.append(loaded)
    result = planners.V075LearnedSupportGraphV1(
        backend_result.route_native_result,
        context,
        tuple(nodes),
        _tuple_strings(
            item["observation_artifact_ref_ids"],
            "graph observation artifact refs",
        ),
        _fraction(
            item["familywise_confidence_error_upper"],
            "graph confidence error",
        ),
    )
    _same(result.to_document(), item, "learned-support graph")
    return result


def _load_behavior(
    document: Any,
) -> planners.V075RowBehaviorBindingV1:
    item = _mapping(document, "row behavior")
    terms = []
    for value in _list(item["terms"], "row-behavior terms"):
        term = _mapping(value, "row-behavior term")
        loaded = planners.V075RobustEventTermV1(
            _enum(
                planners.V075RobustDestinationKindV1,
                term["destination_kind"],
                "robust destination",
            ),
            term["destination_id"],
            _fraction(term["immediate_reward"], "term reward"),
            _fraction(term["lower_probability"], "term lower probability"),
            _fraction(term["upper_probability"], "term upper probability"),
        )
        _same(loaded.to_document(), term, "row-behavior term")
        terms.append(loaded)
    result = planners.V075RowBehaviorBindingV1(
        item["row_id"],
        item["remaining_horizon"],
        tuple(terms),
    )
    _same(result.to_document(), item, "row behavior")
    return result


def _load_cell(document: Any) -> planners.V075QuotientCellV1:
    item = _mapping(document, "quotient cell")
    result = planners.V075QuotientCellV1(
        item["remaining_horizon"],
        _tuple_strings(item["state_node_ids"], "cell state-node IDs"),
        _tuple_strings(item["state_ids"], "cell state IDs"),
        _tuple_strings(item["semantic_keys"], "cell semantic keys"),
    )
    _same(result.to_document(), item, "quotient cell")
    return result


def _load_concretizer(
    document: Any,
) -> planners.V075DistinctActionConcretizerV1:
    item = _mapping(document, "action concretizer")
    result = planners.V075DistinctActionConcretizerV1(
        item["cell_id"],
        item["state_id"],
        item["semantic_key"],
        tuple(
            _action(value, "concretizer ground action")
            for value in _list(
                item["ground_actions"],
                "concretizer ground actions",
            )
        ),
        _tuple_strings(item["row_ids"], "concretizer row IDs"),
        tuple(
            _fraction(value, "concretizer weight")
            for value in _list(
                item["uniform_weights"],
                "concretizer weights",
            )
        ),
    )
    _same(result.to_document(), item, "action concretizer")
    return result


def _load_semantic_action(
    document: Any,
    cells: Mapping[str, planners.V075QuotientCellV1],
) -> planners.V075CompiledSemanticActionV1:
    item = _mapping(document, "semantic action")
    cell = cells.get(item["cell_id"])
    if cell is None:
        _fail("semantic action references an absent quotient cell")
    result = planners.V075CompiledSemanticActionV1(
        cell,
        item["semantic_key"],
        tuple(
            _load_concretizer(value)
            for value in _list(
                item["concretizers"],
                "semantic-action concretizers",
            )
        ),
    )
    _same(result.to_document(), item, "semantic action")
    return result


def _load_quotient(
    document: Any,
    support_graph: planners.V075LearnedSupportGraphV1,
) -> planners.V075ObservationDrivenQuotientV1:
    item = _mapping(document, "observation-driven quotient")
    behaviors = tuple(
        _load_behavior(value)
        for value in _list(item["row_behaviors"], "quotient behaviors")
    )
    cells = tuple(
        _load_cell(value)
        for value in _list(item["cells"], "quotient cells")
    )
    by_id = {value.cell_id: value for value in cells}
    if len(by_id) != len(cells):
        _fail("quotient duplicates a cell")
    semantic_actions = tuple(
        _load_semantic_action(value, by_id)
        for value in _list(
            item["semantic_actions"],
            "quotient semantic actions",
        )
    )
    result = planners.V075ObservationDrivenQuotientV1(
        support_graph,
        behaviors,
        cells,
        semantic_actions,
    )
    _same(result.to_document(), item, "observation-driven quotient")
    return result


def _load_policy_choice(
    document: Any,
) -> planners.V075PolicyStateChoiceV1:
    item = _mapping(document, "policy state choice")
    result = planners.V075PolicyStateChoiceV1(
        item["state_id"],
        tuple(
            _action(value, "policy ground action")
            for value in _list(
                item["ground_actions"],
                "policy ground actions",
            )
        ),
        _tuple_strings(item["row_ids"], "policy row IDs"),
        tuple(
            _fraction(value, "policy uniform weight")
            for value in _list(
                item["uniform_weights"],
                "policy uniform weights",
            )
        ),
    )
    _same(result.to_document(), item, "policy state choice")
    return result


def _load_policy_decision(
    document: Any,
) -> planners.V075DeterministicPolicyDecisionV1:
    item = _mapping(document, "policy decision")
    result = planners.V075DeterministicPolicyDecisionV1(
        _enum(
            planners.V075PlannerRouteV1,
            item["route"],
            "policy-decision route",
        ),
        item["remaining_horizon"],
        item["decision_domain_id"],
        item["selected_option_id"],
        tuple(
            _load_policy_choice(value)
            for value in _list(
                item["state_choices"],
                "policy-decision choices",
            )
        ),
    )
    _same(result.to_document(), item, "policy decision")
    return result


def _load_policy(
    document: Any,
) -> planners.V075DeterministicH2PolicyV1:
    item = _mapping(document, "deterministic H2 policy")
    result = planners.V075DeterministicH2PolicyV1(
        item["learned_support_graph_id"],
        _enum(
            planners.V075PlannerRouteV1,
            item["route"],
            "policy route",
        ),
        item["quotient_id"],
        tuple(
            _load_policy_decision(value)
            for value in _list(item["decisions"], "policy decisions")
        ),
    )
    _same(result.to_document(), item, "deterministic H2 policy")
    return result


def _load_envelope(
    document: Any,
    policy: planners.V075DeterministicH2PolicyV1,
) -> planners.V075RobustH2EnvelopeV1:
    item = _mapping(document, "robust H2 envelope")
    result = planners.V075RobustH2EnvelopeV1(
        policy,
        _fraction(
            item["selected_reward_lower"],
            "selected reward lower",
        ),
        _fraction(
            item["selected_reward_upper"],
            "selected reward upper",
        ),
        _fraction(
            item["unrestricted_reward_upper"],
            "unrestricted reward upper",
        ),
        _fraction(
            item["selected_failure_upper"],
            "selected failure upper",
        ),
        _fraction(
            item["normalized_regret_upper"],
            "normalized regret upper",
        ),
        _fraction(
            item["familywise_confidence_error_upper"],
            "envelope confidence error",
        ),
    )
    _same(result.to_document(), item, "robust H2 envelope")
    return result


def _load_planner_work(
    document: Any,
) -> planners.V075SupportPlannerWorkV1:
    item = _mapping(document, "support-planner work")
    counters = []
    for value in _list(item["counters"], "support-planner counters"):
        counter = _mapping(value, "support-planner counter")
        loaded = planners.V075SupportPlannerCounterV1(
            counter["path"],
            counter["value"],
            counter["observed"],
        )
        _same(loaded.to_document(), counter, "support-planner counter")
        counters.append(loaded)
    result = planners.V075SupportPlannerWorkV1(
        item["learned_support_graph_id"],
        _enum(
            planners.V075PlannerRouteV1,
            item["route"],
            "planner-work route",
        ),
        tuple(counters),
    )
    _same(result.to_document(), item, "support-planner work")
    return result


def _load_planner_result(
    document: Any,
    support_graph: planners.V075LearnedSupportGraphV1,
) -> planners.V075SupportPlannerResultV1:
    item = _mapping(document, "support-planner result")
    quotient_document = item["quotient"]
    quotient = (
        None
        if quotient_document is None
        else _load_quotient(quotient_document, support_graph)
    )
    policy_document = item["policy"]
    policy = (
        None
        if policy_document is None
        else _load_policy(policy_document)
    )
    envelope_document = item["envelope"]
    if envelope_document is None:
        envelope = None
    elif policy is None:
        _fail("planner envelope lacks its transported policy")
    else:
        envelope = _load_envelope(envelope_document, policy)
    result = planners.V075SupportPlannerResultV1(
        support_graph,
        _enum(
            planners.V075PlannerRouteV1,
            item["route"],
            "planner-result route",
        ),
        quotient,
        _enum(
            planners.V075PlannerStatusV1,
            item["status"],
            "planner-result status",
        ),
        policy,
        envelope,
        _tuple_strings(
            item["diagnostic_failed_frontier_row_ids"],
            "diagnostic frontier rows",
        ),
        _load_planner_work(item["work"]),
        item["search_cap"],
    )
    _same(result.to_document(), item, "support-planner result")
    return result


_TRANSPORT_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OperationalPlannerTransportV1:
    _issuer: object = field(repr=False, compare=False)
    occurrence_id: str
    target_tape_namespace_id: str
    context_id: str
    arm: worker.V075WorkerArmV1
    occurrence_ordinal: int
    threshold_profile_id: str
    cap_profile_id: str
    source_transport_id: str | None
    batch_ids: tuple[str, ...]
    backend_result_id: str
    learned_support_graph_id: str
    planner_result_id: str
    backend_bytes: bytes = field(repr=False)
    graph_bytes: bytes = field(repr=False)
    planner_bytes: bytes = field(repr=False)
    _transport_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        for value, label in (
            (self.occurrence_id, "transport occurrence"),
            (
                self.target_tape_namespace_id,
                "transport target namespace",
            ),
            (self.context_id, "transport context"),
            (self.threshold_profile_id, "transport threshold"),
            (self.cap_profile_id, "transport cap profile"),
            (self.backend_result_id, "transport backend result"),
            (
                self.learned_support_graph_id,
                "transport learned-support graph",
            ),
            (self.planner_result_id, "transport planner result"),
        ):
            _cid(value, label)
        if self.source_transport_id is not None:
            _cid(self.source_transport_id, "transport source prior")
        if (
            self._issuer is not _TRANSPORT_ISSUER
            or type(self.arm) is not worker.V075WorkerArmV1
            or type(self.occurrence_ordinal) is not int
            or self.occurrence_ordinal < 0
            or self.batch_ids != tuple(sorted(set(self.batch_ids)))
            or not self.batch_ids
            or (
                self.source_transport_id is not None
            )
            != (
                self.arm
                is worker.V075WorkerArmV1.SOURCE_CONSENSUS_PRIOR
            )
        ):
            _fail("operational planner transport identity is malformed")
        for value in self.batch_ids:
            _cid(value, "transport signed batch")
        backend_document = _canonical_document(
            self.backend_bytes,
            "transport backend document",
        )
        graph_document = _canonical_document(
            self.graph_bytes,
            "transport graph document",
        )
        planner_document = _canonical_document(
            self.planner_bytes,
            "transport planner document",
        )
        if (
            backend_document.get("result_id") != self.backend_result_id
            or backend_document.get("occurrence_id") != self.occurrence_id
            or backend_document.get("arm") != self.arm.value
            or graph_document.get("graph_id")
            != self.learned_support_graph_id
            or graph_document.get("backend_result_id")
            != backend_document.get("route_native_result_id")
            or planner_document.get("result_id") != self.planner_result_id
            or planner_document.get("learned_support_graph_id")
            != self.learned_support_graph_id
            or planner_document.get("route")
            != (
                planners.V075PlannerRouteV1.MATCHED_DIRECT_GROUND.value
                if self.arm
                is worker.V075WorkerArmV1.MATCHED_DIRECT_GROUND
                else planners.V075PlannerRouteV1.ADAPTIVE_QUOTIENT.value
            )
        ):
            _fail("transport child documents cross an identity boundary")
        object.__setattr__(
            self,
            "_transport_id",
            _hash("transport", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_operational_planner_transport.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "occurrence_id": self.occurrence_id,
            "target_tape_namespace_id": self.target_tape_namespace_id,
            "context_id": self.context_id,
            "arm": self.arm.value,
            "occurrence_ordinal": self.occurrence_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "cap_profile_id": self.cap_profile_id,
            "source_transport_id": self.source_transport_id,
            "batch_ids": list(self.batch_ids),
            "backend_result_id": self.backend_result_id,
            "learned_support_graph_id": self.learned_support_graph_id,
            "planner_result_id": self.planner_result_id,
            "backend_bytes_sha256": hashlib.sha256(
                self.backend_bytes
            ).hexdigest(),
            "backend_bytes_hex": self.backend_bytes.hex(),
            "graph_bytes_sha256": hashlib.sha256(
                self.graph_bytes
            ).hexdigest(),
            "graph_bytes_hex": self.graph_bytes.hex(),
            "planner_bytes_sha256": hashlib.sha256(
                self.planner_bytes
            ).hexdigest(),
            "planner_bytes_hex": self.planner_bytes.hex(),
            "child_canonical_documents_only": True,
            "signed_batches_embedded": False,
            "private_material_serialized": False,
            "per_draw_capabilities_materialized": 0,
            "model_compiler_calls": 0,
            "planner_calls": 0,
            "solver_or_search_calls": 0,
            "scientific_plan_certificate": False,
        }

    @property
    def transport_id(self) -> str:
        return self._transport_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "transport_id": self.transport_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def freeze_v075_operational_planner_transport_v1(
    *,
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    backend_result: batch_backend.V075BatchNativeBackendResultV1,
    planner_result: planners.V075SupportPlannerResultV1,
) -> V075OperationalPlannerTransportV1:
    """Serialize child results without recomputing either result."""

    if (
        type(occurrence_identity)
        is not batch_backend.V075BatchNativeOccurrenceIdentityV1
        or type(backend_result)
        is not batch_backend.V075BatchNativeBackendResultV1
        or type(planner_result) is not planners.V075SupportPlannerResultV1
        or backend_result.request.occurrence_identity
        != occurrence_identity
        or planner_result.graph.backend_result
        != backend_result.route_native_result
    ):
        _fail("transport freeze requires one exact child identity graph")
    request = backend_result.request
    if (
        request.arm is not occurrence_identity.arm
        or request.occurrence_ordinal
        != occurrence_identity.occurrence_ordinal
        or request.occurrence_id != occurrence_identity.occurrence_id
        or request.threshold_profile.threshold_profile_id
        != occurrence_identity.threshold_profile_id
        or request.cap_profile.cap_profile_id
        != occurrence_identity.cap_profile_id
        or (
            None
            if request.source_prior_transport is None
            else request.source_prior_transport.transport_id
        )
        != occurrence_identity.source_transport_id
    ):
        _fail("child result differs from its pre-sampling identity")
    return V075OperationalPlannerTransportV1(
        _TRANSPORT_ISSUER,
        occurrence_identity.occurrence_id,
        occurrence_identity.target_tape_namespace_id,
        occurrence_identity.context_id,
        occurrence_identity.arm,
        occurrence_identity.occurrence_ordinal,
        occurrence_identity.threshold_profile_id,
        occurrence_identity.cap_profile_id,
        occurrence_identity.source_transport_id,
        tuple(sorted(item.batch_id for item in request.batches)),
        backend_result.result_id,
        planner_result.graph.graph_id,
        planner_result.result_id,
        backend_result.canonical_bytes,
        canonical_json_bytes(planner_result.graph.to_document()),
        planner_result.canonical_bytes,
    )


def _transport_from_document(
    document: Any,
) -> V075OperationalPlannerTransportV1:
    item = _mapping(document, "operational planner transport")
    backend_bytes = _hex_bytes(
        item["backend_bytes_hex"],
        "transport backend bytes",
    )
    graph_bytes = _hex_bytes(
        item["graph_bytes_hex"],
        "transport graph bytes",
    )
    planner_bytes = _hex_bytes(
        item["planner_bytes_hex"],
        "transport planner bytes",
    )
    if (
        item["backend_bytes_sha256"]
        != hashlib.sha256(backend_bytes).hexdigest()
        or item["graph_bytes_sha256"]
        != hashlib.sha256(graph_bytes).hexdigest()
        or item["planner_bytes_sha256"]
        != hashlib.sha256(planner_bytes).hexdigest()
    ):
        _fail("transport child-document byte digest changed")
    result = V075OperationalPlannerTransportV1(
        _TRANSPORT_ISSUER,
        item["occurrence_id"],
        item["target_tape_namespace_id"],
        item["context_id"],
        _enum(worker.V075WorkerArmV1, item["arm"], "transport arm"),
        item["occurrence_ordinal"],
        item["threshold_profile_id"],
        item["cap_profile_id"],
        item["source_transport_id"],
        _tuple_strings(item["batch_ids"], "transport batch IDs"),
        item["backend_result_id"],
        item["learned_support_graph_id"],
        item["planner_result_id"],
        backend_bytes,
        graph_bytes,
        planner_bytes,
    )
    _same(result.to_document(), item, "operational planner transport")
    return result


_LOAD_ISSUER = object()


@dataclass(frozen=True, slots=True)
class V075OperationalPlannerLoadV1:
    _issuer: object = field(repr=False, compare=False)
    transport: V075OperationalPlannerTransportV1
    backend_result: batch_backend.V075BatchNativeBackendResultV1
    planner_result: planners.V075SupportPlannerResultV1
    _load_id: str = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if (
            self._issuer is not _LOAD_ISSUER
            or type(self.transport)
            is not V075OperationalPlannerTransportV1
            or type(self.backend_result)
            is not batch_backend.V075BatchNativeBackendResultV1
            or type(self.planner_result)
            is not planners.V075SupportPlannerResultV1
            or self.backend_result.result_id
            != self.transport.backend_result_id
            or self.planner_result.graph.graph_id
            != self.transport.learned_support_graph_id
            or self.planner_result.result_id
            != self.transport.planner_result_id
            or self.planner_result.graph.backend_result
            != self.backend_result.route_native_result
        ):
            _fail("loaded operational planner identity graph is malformed")
        object.__setattr__(
            self,
            "_load_id",
            _hash("load", self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.v075_operational_planner_load.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "transport_id": self.transport.transport_id,
            "occurrence_id": self.transport.occurrence_id,
            "backend_result_id": self.backend_result.result_id,
            "learned_support_graph_id": self.planner_result.graph.graph_id,
            "planner_result_id": self.planner_result.result_id,
            "exact_existing_dataclasses_reconstructed": True,
            "total_lift_lineage_input_compatible": True,
            "signed_batches_reverified": True,
            "child_canonical_bytes_verified": True,
            "model_compiler_calls": 0,
            "planner_calls": 0,
            "solver_or_search_calls": 0,
            "private_material_loaded": False,
            "per_draw_capabilities_materialized": 0,
            "scientific_plan_certificate": False,
        }

    @property
    def load_id(self) -> str:
        return self._load_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "load_id": self.load_id}


def load_v075_operational_planner_transport_v1(
    *,
    occurrence_identity: (
        batch_backend.V075BatchNativeOccurrenceIdentityV1
    ),
    batches: tuple[batched.V075SignedBatchedObservationV1, ...],
    source_prior_transport: worker.V075SourcePriorTransportV1 | None,
    claimed_bytes: bytes,
) -> V075OperationalPlannerLoadV1:
    """Load exact child results without invoking any compiler or planner."""

    try:
        if (
            type(occurrence_identity)
            is not batch_backend.V075BatchNativeOccurrenceIdentityV1
            or type(batches) is not tuple
            or not batches
            or any(
                type(item) is not batched.V075SignedBatchedObservationV1
                for item in batches
            )
            or (
                source_prior_transport is not None
                and type(source_prior_transport)
                is not worker.V075SourcePriorTransportV1
            )
        ):
            _fail("operational transport inputs are untyped")
        transport = _transport_from_document(
            _canonical_document(
                claimed_bytes,
                "operational planner transport bytes",
            )
        )
        source_id = (
            None
            if source_prior_transport is None
            else source_prior_transport.transport_id
        )
        if (
            transport.occurrence_id != occurrence_identity.occurrence_id
            or transport.target_tape_namespace_id
            != occurrence_identity.target_tape_namespace_id
            or transport.context_id != occurrence_identity.context_id
            or transport.arm is not occurrence_identity.arm
            or transport.occurrence_ordinal
            != occurrence_identity.occurrence_ordinal
            or transport.threshold_profile_id
            != occurrence_identity.threshold_profile_id
            or transport.cap_profile_id
            != occurrence_identity.cap_profile_id
            or transport.source_transport_id != source_id
            or transport.source_transport_id
            != occurrence_identity.source_transport_id
            or transport.batch_ids
            != tuple(sorted(item.batch_id for item in batches))
        ):
            _fail("transport differs from parent-owned typed inputs")
        request = (
            batch_backend.freeze_v075_batch_native_backend_request_v1(
                arm=occurrence_identity.arm,
                occurrence_ordinal=occurrence_identity.occurrence_ordinal,
                batches=batches,
                source_prior_transport=source_prior_transport,
                occurrence_identity=occurrence_identity,
            )
        )
        backend_result = _load_backend_result(
            _canonical_document(
                transport.backend_bytes,
                "child backend result",
            ),
            request,
        )
        support_graph = _load_graph(
            _canonical_document(
                transport.graph_bytes,
                "child learned-support graph",
            ),
            backend_result,
        )
        planner_result = _load_planner_result(
            _canonical_document(
                transport.planner_bytes,
                "child planner result",
            ),
            support_graph,
        )
        return V075OperationalPlannerLoadV1(
            _LOAD_ISSUER,
            transport,
            backend_result,
            planner_result,
        )
    except V075OperationalPlannerTransportInvariantViolation:
        raise
    except (
        AttributeError,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise V075OperationalPlannerTransportInvariantViolation(
            f"operational planner transport reconstruction failed: {error}"
        ) from error


__all__ = [
    "DOMAIN_TAGS",
    "MODEL_COMPILATION_ALLOWED",
    "PER_DRAW_CAPABILITY_EXPANSION_ALLOWED",
    "PLANNER_EXECUTION_ALLOWED",
    "PRIVATE_MATERIAL_ALLOWED",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "SOLVER_OR_SEARCH_ALLOWED",
    "V075OperationalPlannerLoadV1",
    "V075OperationalPlannerTransportInvariantViolation",
    "V075OperationalPlannerTransportV1",
    "freeze_v075_operational_planner_transport_v1",
    "load_v075_operational_planner_transport_v1",
]
