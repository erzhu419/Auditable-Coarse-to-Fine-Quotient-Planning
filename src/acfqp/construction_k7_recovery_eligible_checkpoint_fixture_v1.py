"""Freeze an as-of checkpoint whose failed proof still permits local recovery.

The capped persistent-cache baseline remains unchanged.  This additive
construction fixture takes its transaction-1 source graph from the already
verified source-to-target proof transition and publishes only that immutable
as-of graph to a fresh query.  The later target graph is used offline to prove
lineage but is not an input to the online query/consumption/request functions.

The fresh query reuses all forty-one proof nodes.  Only after the cached proof
fails does this module freeze the six frontier rows with one registered next
checkpoint; the seventh, cap-blocked row remains explicit.  No namespace,
observer, signer, kernel, private law, tape, or ground access is accepted here.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_persistent_proof_cache_v1 as cache_v1
from acfqp import construction_k7_query_bound_rapm_proof_dependency_dag_v1 as dag_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_CONSUMPTION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.110"
PROFILE_KEY = "construction_k7_recovery_eligible_checkpoint_fixture_v1"

CHECKPOINT_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_QUERY_V1_DOMAIN
CONSUMPTION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_CONSUMPTION_V1_DOMAIN
)
ROW_REQUEST_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN
REQUEST_DOMAIN = CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {
        CHECKPOINT_DOMAIN,
        QUERY_DOMAIN,
        CONSUMPTION_DOMAIN,
        ROW_REQUEST_DOMAIN,
        REQUEST_DOMAIN,
    }
)
if len(LOCAL_DOMAINS) != 5 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery-eligible checkpoint domains are not central")

_CHECKPOINT_ISSUER = object()
_QUERY_ISSUER = object()
_CONSUMPTION_ISSUER = object()
_ROW_ISSUER = object()
_REQUEST_ISSUER = object()


class ConstructionK7RecoveryEligibleCheckpointFixtureV1Error(ValueError):
    """The as-of graph, fresh query, or no-access request changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleCheckpointFixtureV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleCheckpointFixtureV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _same_document(left: Any, right: Any) -> bool:
    try:
        return canonical_json_bytes(left) == canonical_json_bytes(right)
    except (TypeError, ValueError):
        return False


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCheckpointV1:
    _issuer: InitVar[object]
    source_persistent_cache_id: str
    source_bundle_binding_id: str
    source_logical_occurrence_id: str
    source_final_local_replanning_id: str
    source_graph_id: str
    source_graph_bytes: bytes = field(repr=False)
    model: planning_v2.V075NumericalModelV2 = field(repr=False)
    proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    node_inventory: tuple[tuple[str, str], ...]
    _checkpoint_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CHECKPOINT_ISSUER
            or type(self.source_graph_bytes) is not bytes
            or not self.source_graph_bytes
            or type(self.model) is not planning_v2.V075NumericalModelV2
            or type(self.proof) is not planning_v2.V075NumericalPlanningProofV2
            or type(self.node_inventory) is not tuple
            or len(self.node_inventory) != 41
            or len(set(self.node_inventory)) != 41
        ):
            _fail("recovery-eligible checkpoint is caller-minted")
        for value, label in (
            (self.source_persistent_cache_id, "source persistent cache"),
            (self.source_bundle_binding_id, "source-bundle binding"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.source_final_local_replanning_id, "source final-local replanning"),
            (self.source_graph_id, "source proof graph"),
        ):
            _cid(value, label)
        self.model.__post_init__()
        self.proof.__post_init__()
        frontier = self.proof.failed_frontier
        if (
            self.proof.model != self.model
            or self.proof.route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.proof.outcome
            is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
            or frontier is None
            or self.requestable_frontier_row_count != 6
            or self.cap_blocked_frontier_row_count != 1
            or self.requested_additional_draw_count != 12_288
        ):
            _fail("recovery-eligible checkpoint proof or frontier changed")
        graph = loads_canonical_json(self.source_graph_bytes)
        if (
            type(graph) is not dict
            or canonical_json_bytes(graph) != self.source_graph_bytes
            or graph.get("proof_dependency_graph_id") != self.source_graph_id
            or not _same_document(graph.get("numerical_model"), self.model.to_document())
            or not _same_document(graph.get("numerical_proof"), self.proof.to_document())
            or tuple(
                (item["role_key"], item["proof_dependency_node_id"])
                for item in graph.get("nodes", ())
            )
            != self.node_inventory
        ):
            _fail("recovery-eligible checkpoint crossed its source graph")
        object.__setattr__(
            self,
            "_checkpoint_id",
            content_id(CHECKPOINT_DOMAIN, self._payload()),
        )

    @property
    def requestable_frontier_row_count(self) -> int:
        frontier = self.proof.failed_frontier
        assert frontier is not None
        return sum(
            item.next_registered_checkpoint is not None
            for item in frontier.obligations
        )

    @property
    def cap_blocked_frontier_row_count(self) -> int:
        frontier = self.proof.failed_frontier
        assert frontier is not None
        return len(frontier.obligations) - self.requestable_frontier_row_count

    @property
    def requested_additional_draw_count(self) -> int:
        frontier = self.proof.failed_frontier
        assert frontier is not None
        return sum(
            0
            if item.next_registered_checkpoint is None
            else item.next_registered_checkpoint
            - item.current_validation_draw_count
            for item in frontier.obligations
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.proof.failed_frontier
        assert frontier is not None
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_checkpoint_fixture.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_persistent_proof_cache_id": self.source_persistent_cache_id,
            "source_bundle_binding_id": self.source_bundle_binding_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "source_final_local_replanning_id": self.source_final_local_replanning_id,
            "source_proof_dependency_graph_id": self.source_graph_id,
            "published_numerical_model_id": self.model.model_id,
            "published_numerical_proof_id": self.proof.proof_id,
            "published_failed_frontier_id": frontier.frontier_id,
            "proof_node_ids": [node_id for _role, node_id in self.node_inventory],
            "proof_node_count": len(self.node_inventory),
            "frontier_row_count": len(frontier.obligations),
            "requestable_frontier_row_count": self.requestable_frontier_row_count,
            "cap_blocked_frontier_row_count": self.cap_blocked_frontier_row_count,
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "publication_cut": "TRANSACTION_1_REPLANNING_AS_OF_CHECKPOINT",
            "immutable_as_of_checkpoint": True,
            "later_target_graph_input_present_in_online_api": False,
            "deliberately_coarsened_partition_used": False,
            "production_latest_epoch_selection_authority": False,
            "construction_fixture": True,
            "portable_checkpoint_loader_present": False,
            "ground_access_count": 0,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
            "next_required_action": "RUN_FRESH_QUERY_ON_PUBLISHED_CHECKPOINT",
        }

    @property
    def checkpoint_id(self) -> str:
        current = content_id(CHECKPOINT_DOMAIN, self._payload())
        if current != self._checkpoint_id:
            _fail("recovery-eligible checkpoint changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "source_graph": loads_canonical_json(self.source_graph_bytes),
            "recovery_eligible_checkpoint_id": self.checkpoint_id,
        }


def materialize_recovery_eligible_checkpoint_fixture_v1(
    persistent_cache_bytes: bytes,
) -> RecoveryEligibleCheckpointV1:
    """Offline-only materialization from the exact source-to-target transition."""

    persistent = cache_v1.load_query_bound_persistent_proof_cache_bytes_v1(
        persistent_cache_bytes
    )
    binding = loads_canonical_json(persistent.source_bundle_binding_bytes)
    transition = dag_v1.replay_query_bound_rapm_proof_dependency_transition_bytes_v1(
        persistent.proof_dependency_transition_bytes
    )
    transition_document = transition.to_document()
    source_graph_document = transition_document["source_graph"]
    target_graph_document = transition_document["target_graph"]
    if (
        target_graph_document["numerical_model_id"] != persistent.target_model.model_id
        or target_graph_document["numerical_proof_id"]
        != loads_canonical_json(persistent.target_proof_bytes)["proof_id"]
        or transition.source_final_local_replanning_id
        != binding["source_final_local_replanning_id"]
    ):
        _fail("recovery-eligible source graph crossed the persistent cache")
    source_graph = transition.source_graph
    inventory = tuple(
        (item["role_key"], item["proof_dependency_node_id"])
        for item in source_graph_document["nodes"]
    )
    return RecoveryEligibleCheckpointV1(
        _CHECKPOINT_ISSUER,
        persistent.cache_id,
        binding["query_bound_reusable_rapm_source_bundle_binding_id"],
        binding["logical_occurrence_id"],
        transition.source_final_local_replanning_id,
        source_graph_document["proof_dependency_graph_id"],
        canonical_json_bytes(source_graph_document),
        source_graph.model,
        source_graph.proof,
        inventory,
    )


def require_recovery_eligible_checkpoint_v1(
    checkpoint: RecoveryEligibleCheckpointV1,
) -> RecoveryEligibleCheckpointV1:
    if type(checkpoint) is not RecoveryEligibleCheckpointV1:
        _fail("recovery-eligible checkpoint has a foreign type")
    checkpoint.__post_init__(_CHECKPOINT_ISSUER)
    return checkpoint


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCheckpointQueryV1:
    _issuer: InitVar[object]
    checkpoint_id: str
    model_id: str
    source_logical_occurrence_id: str
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("recovery-eligible query is caller-minted")
        for value, label in (
            (self.checkpoint_id, "recovery-eligible checkpoint"),
            (self.model_id, "published numerical model"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.logical_occurrence_id, "fresh logical occurrence"),
            (self.threshold_profile_id, "threshold profile"),
        ):
            _cid(value, label)
        if (
            self.logical_occurrence_id == self.source_logical_occurrence_id
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 1
            or self.threshold_profile_id
            != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        ):
            _fail("recovery-eligible fresh query identity changed")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_checkpoint_query.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_eligible_checkpoint_id": self.checkpoint_id,
            "published_numerical_model_id": self.model_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "route": "ADAPTIVE_QUOTIENT",
            "ground_input_present": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("recovery-eligible query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "recovery_eligible_query_id": self.query_id}


def freeze_recovery_eligible_checkpoint_query_v1(
    checkpoint: RecoveryEligibleCheckpointV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> RecoveryEligibleCheckpointQueryV1:
    checkpoint = require_recovery_eligible_checkpoint_v1(checkpoint)
    return RecoveryEligibleCheckpointQueryV1(
        _QUERY_ISSUER,
        checkpoint.checkpoint_id,
        checkpoint.model.model_id,
        checkpoint.source_logical_occurrence_id,
        _cid(logical_occurrence_id, "fresh logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
    )


@dataclass(frozen=True, slots=True)
class RecoveryEligibleCheckpointConsumptionV1:
    _issuer: InitVar[object]
    checkpoint: RecoveryEligibleCheckpointV1 = field(repr=False)
    query: RecoveryEligibleCheckpointQueryV1
    _consumption_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CONSUMPTION_ISSUER
            or type(self.checkpoint) is not RecoveryEligibleCheckpointV1
            or type(self.query) is not RecoveryEligibleCheckpointQueryV1
        ):
            _fail("recovery-eligible cache consumption is caller-minted")
        self.checkpoint.__post_init__(_CHECKPOINT_ISSUER)
        self.query.__post_init__(_QUERY_ISSUER)
        if (
            self.query.checkpoint_id != self.checkpoint.checkpoint_id
            or self.query.model_id != self.checkpoint.model.model_id
            or self.query.source_logical_occurrence_id
            != self.checkpoint.source_logical_occurrence_id
        ):
            _fail("recovery-eligible query crossed its checkpoint")
        object.__setattr__(
            self,
            "_consumption_id",
            content_id(CONSUMPTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.checkpoint.proof.failed_frontier
        assert frontier is not None
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_checkpoint_consumption.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_eligible_checkpoint_id": self.checkpoint.checkpoint_id,
            "recovery_eligible_query_id": self.query.query_id,
            "logical_occurrence_id": self.query.logical_occurrence_id,
            "published_numerical_model_id": self.checkpoint.model.model_id,
            "cached_numerical_proof_id": self.checkpoint.proof.proof_id,
            "cached_failed_frontier_id": frontier.frontier_id,
            "reused_proof_node_ids": [
                node_id for _role, node_id in self.checkpoint.node_inventory
            ],
            "proof_node_reuse_count": len(self.checkpoint.node_inventory),
            "proof_node_compute_count": 0,
            "full_planner_call_count": 0,
            "model_construction_repeated": False,
            "new_ground_access_count": 0,
            "exact_cached_certificate_failure_replayed": True,
            "requestable_frontier_row_count": self.checkpoint.requestable_frontier_row_count,
            "cap_blocked_frontier_row_count": self.checkpoint.cap_blocked_frontier_row_count,
            "query_local_ground_recovery_eligible": True,
            "query_local_ground_recovery_executed_here": False,
            "next_required_action": "FREEZE_MINIMAL_RECOVERY_REQUEST",
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def consumption_id(self) -> str:
        current = content_id(CONSUMPTION_DOMAIN, self._payload())
        if current != self._consumption_id:
            _fail("recovery-eligible consumption changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query": self.query.to_document(),
            "recovery_eligible_checkpoint_consumption_id": self.consumption_id,
        }


def consume_recovery_eligible_checkpoint_v1(
    checkpoint: RecoveryEligibleCheckpointV1,
    query: RecoveryEligibleCheckpointQueryV1,
) -> RecoveryEligibleCheckpointConsumptionV1:
    return RecoveryEligibleCheckpointConsumptionV1(
        _CONSUMPTION_ISSUER,
        require_recovery_eligible_checkpoint_v1(checkpoint),
        query,
    )


@dataclass(frozen=True, slots=True)
class RecoveryEligibleValidationRequestV1:
    _issuer: InitVar[object]
    numerical_row_id: str
    semantic_row_binding_id: str
    current_validation_draw_count: int
    next_registered_checkpoint: int | None
    requested_additional_draw_count: int
    disposition: str
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ROW_ISSUER:
            _fail("recovery-eligible row request is caller-minted")
        _cid(self.numerical_row_id, "recovery-eligible numerical row")
        _cid(self.semantic_row_binding_id, "recovery-eligible row binding")
        requested = self.disposition == "REQUEST_NEXT_REGISTERED_CHECKPOINT"
        blocked = self.disposition == "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
        if (
            type(self.current_validation_draw_count) is not int
            or self.current_validation_draw_count <= 0
            or not (requested or blocked)
            or (
                requested
                and (
                    type(self.next_registered_checkpoint) is not int
                    or self.next_registered_checkpoint
                    <= self.current_validation_draw_count
                    or self.requested_additional_draw_count
                    != self.next_registered_checkpoint
                    - self.current_validation_draw_count
                )
            )
            or (
                blocked
                and (
                    self.next_registered_checkpoint is not None
                    or self.requested_additional_draw_count != 0
                )
            )
        ):
            _fail("recovery-eligible row request semantics changed")
        object.__setattr__(
            self,
            "_request_id",
            content_id(ROW_REQUEST_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_validation_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "numerical_row_id": self.numerical_row_id,
            "semantic_row_binding_id": self.semantic_row_binding_id,
            "current_validation_draw_count": self.current_validation_draw_count,
            "next_registered_checkpoint": self.next_registered_checkpoint,
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "disposition": self.disposition,
            "selected_from_cached_failed_frontier": True,
            "ground_access_performed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(ROW_REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("recovery-eligible row request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "validation_request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class RecoveryEligibleRecoveryRequestV1:
    _issuer: InitVar[object]
    checkpoint: RecoveryEligibleCheckpointV1 = field(repr=False)
    consumption: RecoveryEligibleCheckpointConsumptionV1 = field(repr=False)
    rows: tuple[RecoveryEligibleValidationRequestV1, ...]
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _REQUEST_ISSUER
            or type(self.checkpoint) is not RecoveryEligibleCheckpointV1
            or type(self.consumption) is not RecoveryEligibleCheckpointConsumptionV1
            or type(self.rows) is not tuple
            or any(type(item) is not RecoveryEligibleValidationRequestV1 for item in self.rows)
        ):
            _fail("recovery-eligible recovery request is caller-minted")
        self.checkpoint.__post_init__(_CHECKPOINT_ISSUER)
        self.consumption.__post_init__(_CONSUMPTION_ISSUER)
        for row in self.rows:
            row.__post_init__(_ROW_ISSUER)
        if (
            self.consumption.checkpoint.checkpoint_id != self.checkpoint.checkpoint_id
            or len(self.requested_rows) != 6
            or len(self.cap_blocked_rows) != 1
            or self.requested_additional_draw_count != 12_288
            or tuple(item.numerical_row_id for item in self.rows)
            != tuple(sorted({item.numerical_row_id for item in self.rows}))
        ):
            _fail("recovery-eligible recovery request inventory changed")
        object.__setattr__(
            self,
            "_request_id",
            content_id(REQUEST_DOMAIN, self._payload()),
        )

    @property
    def requested_rows(self) -> tuple[RecoveryEligibleValidationRequestV1, ...]:
        return tuple(
            item
            for item in self.rows
            if item.disposition == "REQUEST_NEXT_REGISTERED_CHECKPOINT"
        )

    @property
    def cap_blocked_rows(self) -> tuple[RecoveryEligibleValidationRequestV1, ...]:
        return tuple(
            item
            for item in self.rows
            if item.disposition == "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
        )

    @property
    def requested_additional_draw_count(self) -> int:
        return sum(item.requested_additional_draw_count for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        frontier = self.checkpoint.proof.failed_frontier
        assert frontier is not None
        query = self.consumption.query
        return {
            "schema": "acfqp.construction_k7_recovery_eligible_recovery_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_eligible_checkpoint_id": self.checkpoint.checkpoint_id,
            "recovery_eligible_checkpoint_consumption_id": self.consumption.consumption_id,
            "recovery_eligible_query_id": query.query_id,
            "logical_occurrence_id": query.logical_occurrence_id,
            "source_numerical_model_id": self.checkpoint.model.model_id,
            "source_numerical_proof_id": self.checkpoint.proof.proof_id,
            "source_frontier_id": frontier.frontier_id,
            "transaction_index": 1,
            "maximum_local_transactions_per_logical_occurrence": 2,
            "validation_request_ids": [item.request_id for item in self.rows],
            "requested_row_count": len(self.requested_rows),
            "cap_blocked_row_count": len(self.cap_blocked_rows),
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "selection_rule": "ALL_AND_ONLY_CACHED_FRONTIER_ROWS_WITH_NEXT_REGISTERED_CHECKPOINT",
            "activation_state": "PREPARED_NO_ACCESS",
            "request_frozen_after_exact_cached_certificate_failure": True,
            "request_frozen_before_namespace_creation": True,
            "observer_input_present": False,
            "signer_input_present": False,
            "kernel_input_present": False,
            "private_law_input_present": False,
            "ground_tape_input_present": False,
            "ground_access_count": 0,
            "ground_execution_authorized_here": False,
            "next_required_action": "CREATE_FRESH_NAMESPACE_AND_EXECUTE_MINIMAL_RECOVERY",
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("recovery-eligible recovery request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_requests": [item.to_document() for item in self.rows],
            "recovery_eligible_recovery_request_id": self.request_id,
        }


def prepare_recovery_eligible_recovery_request_v1(
    checkpoint: RecoveryEligibleCheckpointV1,
    consumption: RecoveryEligibleCheckpointConsumptionV1,
) -> RecoveryEligibleRecoveryRequestV1:
    checkpoint = require_recovery_eligible_checkpoint_v1(checkpoint)
    if type(consumption) is not RecoveryEligibleCheckpointConsumptionV1:
        _fail("recovery-eligible consumption has a foreign type")
    consumption.__post_init__(_CONSUMPTION_ISSUER)
    frontier = checkpoint.proof.failed_frontier
    assert frontier is not None
    rows_by_id = {item.row_id: item for item in checkpoint.model.rows}
    rows = []
    for obligation in frontier.obligations:
        row = rows_by_id.get(obligation.row_id)
        if row is None or obligation.unmaterialized_successor_ids:
            _fail("cached frontier row is absent or structurally incomplete")
        next_checkpoint = obligation.next_registered_checkpoint
        rows.append(
            RecoveryEligibleValidationRequestV1(
                _ROW_ISSUER,
                row.row_id,
                row.row_binding_id,
                obligation.current_validation_draw_count,
                next_checkpoint,
                (
                    0
                    if next_checkpoint is None
                    else next_checkpoint - obligation.current_validation_draw_count
                ),
                (
                    "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
                    if next_checkpoint is None
                    else "REQUEST_NEXT_REGISTERED_CHECKPOINT"
                ),
            )
        )
    return RecoveryEligibleRecoveryRequestV1(
        _REQUEST_ISSUER,
        checkpoint,
        consumption,
        tuple(sorted(rows, key=lambda item: item.numerical_row_id)),
    )


def require_recovery_eligible_recovery_request_v1(
    request: RecoveryEligibleRecoveryRequestV1,
) -> RecoveryEligibleRecoveryRequestV1:
    if type(request) is not RecoveryEligibleRecoveryRequestV1:
        _fail("recovery-eligible recovery request has a foreign type")
    request.__post_init__(_REQUEST_ISSUER)
    return request


__all__ = [
    "ConstructionK7RecoveryEligibleCheckpointFixtureV1Error",
    "LOCAL_DOMAINS",
    "RecoveryEligibleCheckpointConsumptionV1",
    "RecoveryEligibleCheckpointQueryV1",
    "RecoveryEligibleCheckpointV1",
    "RecoveryEligibleRecoveryRequestV1",
    "RecoveryEligibleValidationRequestV1",
    "consume_recovery_eligible_checkpoint_v1",
    "freeze_recovery_eligible_checkpoint_query_v1",
    "materialize_recovery_eligible_checkpoint_fixture_v1",
    "prepare_recovery_eligible_recovery_request_v1",
    "require_recovery_eligible_checkpoint_v1",
    "require_recovery_eligible_recovery_request_v1",
]
