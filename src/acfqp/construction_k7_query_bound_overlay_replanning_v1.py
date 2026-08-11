"""Compile one query-bound ground transaction and replan the same query.

This is the construction bridge from local signed ground evidence back to the
reusable abstract world model.  It preserves the source model's frozen support,
adds only the requested validation counts, maps unseen outcomes to OTHER,
recomputes exact confidence intervals, and reruns the prior-free H=2 planner.
No observer, kernel, private law, or ground tape is accessed after the closed
transaction.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_ground_transaction_v1 as ground_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_OVERLAY_REPLANNING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.89"
PROFILE_KEY = "construction_k7_query_bound_overlay_replanning_v1"

RESULT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_OVERLAY_REPLANNING_V1_DOMAIN
LOCAL_DOMAINS = frozenset({RESULT_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound overlay-replanning domain is not central")

_RESULT_ISSUER = object()


class ConstructionK7QueryBoundOverlayReplanningV1Error(ValueError):
    """The transaction, numerical overlay, or exact replanning changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundOverlayReplanningV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundOverlayReplanningV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class QueryBoundOverlayReplanningV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    transaction: ground_v1.QueryBoundGroundTransactionV1 = field(repr=False)
    source_model_epoch_id: str
    source_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    source_proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    deltas: tuple[planning_v2.V075QueryBoundValidationDeltaV2, ...] = field(
        repr=False
    )
    successor_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    successor_proof: planning_v2.V075NumericalPlanningProofV2 = field(
        repr=False
    )
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.transaction)
            is not ground_v1.QueryBoundGroundTransactionV1
            or type(self.source_model) is not planning_v2.V075NumericalModelV2
            or type(self.source_proof)
            is not planning_v2.V075NumericalPlanningProofV2
            or type(self.deltas) is not tuple
            or not self.deltas
            or any(
                type(item) is not planning_v2.V075QueryBoundValidationDeltaV2
                for item in self.deltas
            )
            or type(self.successor_model)
            is not planning_v2.V075NumericalModelV2
            or type(self.successor_proof)
            is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("query-bound overlay replanning result is caller-minted")
        _cid(self.source_operational_trace_id, "source operational trace")
        _cid(self.source_model_epoch_id, "source model epoch")
        ground_v1.verify_query_bound_ground_transaction_v1(self.transaction)
        request = self.transaction.request
        source_frontier = self.source_proof.failed_frontier
        if (
            request.source_operational_trace_id
            != self.source_operational_trace_id
            or request.overlay_model_epoch_id != self.source_model_epoch_id
            or request.overlay_model_id != self.source_model.model_id
            or request.overlay_proof_id != self.source_proof.proof_id
            or source_frontier is None
            or request.overlay_frontier_id != source_frontier.frontier_id
            or self.source_proof.model != self.source_model
            or self.source_proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.successor_proof.model != self.successor_model
            or self.successor_proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or tuple(item.source_row_id for item in self.deltas)
            != tuple(sorted({item.source_row_id for item in self.deltas}))
            or {item.source_model_id for item in self.deltas}
            != {self.source_model.model_id}
            or len(self.deltas) != len(self.transaction.row_executions)
        ):
            _fail("query-bound overlay replanning identity graph crossed")
        source_by_binding = {
            item.row_binding_id: item for item in self.source_model.rows
        }
        successor_by_binding = {
            item.row_binding_id: item for item in self.successor_model.rows
        }
        if (
            len(source_by_binding) != len(self.source_model.rows)
            or len(successor_by_binding) != len(self.successor_model.rows)
            or set(source_by_binding) != set(successor_by_binding)
            or self.source_model.context != self.successor_model.context
            or self.source_model.evidence_kind
            != self.successor_model.evidence_kind
        ):
            _fail("query-bound successor changed the reusable model closure")
        delta_by_binding = {item.row_binding_id: item for item in self.deltas}
        if set(delta_by_binding) != set(self.changed_row_binding_ids):
            _fail("query-bound successor changed rows outside the signed deltas")
        for binding_id, source_row in source_by_binding.items():
            successor_row = successor_by_binding[binding_id]
            delta = delta_by_binding.get(binding_id)
            if delta is None:
                if source_row.to_document() != successor_row.to_document():
                    _fail("query-bound overlay changed an unrequested row")
            elif (
                delta.source_row_id != source_row.row_id
                or delta.source_validation_draw_count
                != source_row.validation_draw_count
                or delta.target_validation_draw_count
                != successor_row.validation_draw_count
                or tuple(item.to_document() for item in source_row.support)
                != tuple(item.to_document() for item in successor_row.support)
            ):
                _fail("query-bound overlay changed support or checkpoint semantics")
        object.__setattr__(
            self,
            "_result_id",
            content_id(RESULT_DOMAIN, self._payload()),
        )

    @property
    def changed_row_binding_ids(self) -> tuple[str, ...]:
        source = {item.row_binding_id: item.row_id for item in self.source_model.rows}
        successor = {
            item.row_binding_id: item.row_id for item in self.successor_model.rows
        }
        return tuple(
            sorted(
                binding_id
                for binding_id in source
                if successor.get(binding_id) != source[binding_id]
            )
        )

    @property
    def preserved_row_binding_ids(self) -> tuple[str, ...]:
        changed = set(self.changed_row_binding_ids)
        return tuple(
            sorted(
                item.row_binding_id
                for item in self.source_model.rows
                if item.row_binding_id not in changed
            )
        )

    @property
    def source_validation_draw_count(self) -> int:
        return sum(item.source_validation_draw_count for item in self.deltas)

    @property
    def added_validation_draw_count(self) -> int:
        return sum(item.additional_validation_draw_count for item in self.deltas)

    @property
    def successor_validation_draw_count(self) -> int:
        return sum(item.target_validation_draw_count for item in self.deltas)

    def _payload(self) -> dict[str, Any]:
        frontier = self.successor_proof.failed_frontier
        failed = frontier is not None
        return {
            "schema": "acfqp.construction_k7_query_bound_overlay_replanning.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "logical_occurrence_id": self.transaction.request.logical_occurrence_id,
            "reusable_abstract_query_id": (
                self.transaction.request.reusable_abstract_query_id
            ),
            "root_query_result_id": self.transaction.request.root_query_result_id,
            "query_bound_recovery_overlay_id": (
                self.transaction.request.query_bound_recovery_overlay_id
            ),
            "query_bound_recovery_request_id": self.transaction.request.request_id,
            "query_bound_ground_transaction_id": self.transaction.transaction_id,
            "transaction_index": self.transaction.request.transaction_index,
            "source_model_epoch_id": self.source_model_epoch_id,
            "source_numerical_model_id": self.source_model.model_id,
            "source_numerical_proof_id": self.source_proof.proof_id,
            "source_frontier_id": self.source_proof.failed_frontier.frontier_id,
            "validation_delta_ids": [item.delta_id for item in self.deltas],
            "successor_numerical_model_id": self.successor_model.model_id,
            "successor_numerical_proof_id": self.successor_proof.proof_id,
            "successor_outcome": self.successor_proof.outcome.value,
            "successor_frontier_id": (
                None if frontier is None else frontier.frontier_id
            ),
            "changed_semantic_row_binding_ids": list(
                self.changed_row_binding_ids
            ),
            "preserved_semantic_row_binding_ids": list(
                self.preserved_row_binding_ids
            ),
            "source_row_count": len(self.source_model.rows),
            "successor_row_count": len(self.successor_model.rows),
            "changed_row_count": len(self.changed_row_binding_ids),
            "preserved_row_count": len(self.preserved_row_binding_ids),
            "source_validation_draw_count_on_changed_rows": (
                self.source_validation_draw_count
            ),
            "added_signed_validation_draw_count": (
                self.added_validation_draw_count
            ),
            "successor_validation_draw_count_on_changed_rows": (
                self.successor_validation_draw_count
            ),
            "signed_batch_deltas_exactly_replayed": True,
            "old_support_frozen_and_reused": True,
            "unseen_delta_outcomes_projected_to_other": True,
            "unrequested_rows_byte_identical": True,
            "immutable_query_local_model_compiled": True,
            "same_query_replanned": True,
            "ground_access_after_closed_transaction": 0,
            "observer_input_during_compilation": False,
            "kernel_input_during_compilation": False,
            "private_law_input_during_compilation": False,
            "fresh_query_recovery_loop_closed_through_replanning": True,
            "proof_still_failed": failed,
            "next_required_action": (
                "FREEZE_TRANSACTION_2_OR_ROUTE_TO_FALLBACK"
                if failed
                else "INDEPENDENT_TOTAL_LIFT_AND_PLAN_CERTIFICATE_AUDIT"
            ),
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("query-bound overlay replanning result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_deltas": [item.to_document() for item in self.deltas],
            "successor_model": self.successor_model.to_document(),
            "successor_proof": self.successor_proof.to_document(),
            "query_bound_overlay_replanning_id": self.result_id,
        }


def _source_model_and_proof(
    *,
    source_trace_bytes: bytes,
    transaction: ground_v1.QueryBoundGroundTransactionV1,
) -> tuple[str, planning_v2.V075NumericalModelV2, planning_v2.V075NumericalPlanningProofV2]:
    try:
        trace = loads_canonical_json(source_trace_bytes)
        chain = trace["causal_recovery_chain"]
        epoch = chain["final_model_epoch"]
        source_trace_id = trace["operational_trace_id"]
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(epoch["model"])
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(epoch["proof"])
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundOverlayReplanningV1Error(
            "query-bound replanning source trace is absent or invalid"
        ) from error
    request = transaction.request
    if (
        source_trace_id != request.source_operational_trace_id
        or epoch["model_epoch_id"] != request.overlay_model_epoch_id
        or model.model_id != request.overlay_model_id
        or proof.proof_id != request.overlay_proof_id
        or proof.model != model
        or proof.failed_frontier is None
        or proof.failed_frontier.frontier_id != request.overlay_frontier_id
    ):
        _fail("query-bound replanning source model crossed the request")
    return epoch["model_epoch_id"], model, proof


def compile_and_replan_query_bound_ground_transaction_v1(
    *,
    source_trace_bytes: bytes,
    transaction: ground_v1.QueryBoundGroundTransactionV1,
) -> QueryBoundOverlayReplanningV1:
    transaction = ground_v1.verify_query_bound_ground_transaction_v1(transaction)
    epoch_id, source_model, source_proof = _source_model_and_proof(
        source_trace_bytes=source_trace_bytes,
        transaction=transaction,
    )
    appends_by_batch = {
        item.batch.batch_id: item for item in transaction.observer_closure.appends
    }
    if len(appends_by_batch) != len(transaction.observer_closure.appends):
        _fail("query-bound ground transaction duplicated a signed batch")
    request_by_id = {
        item.request_id: item for item in transaction.request.requested_rows
    }
    deltas = []
    for execution in transaction.row_executions:
        request = request_by_id.get(execution.validation_request_id)
        append = appends_by_batch.get(execution.validation_batch_id)
        if (
            request is None
            or append is None
            or append.receipt.receipt_id
            != execution.validation_append_receipt_id
            or append.batch.request.stream_identity.row_binding_id
            != execution.semantic_row_binding_id
            or append.batch.request.accepted_draw_count
            != request.requested_additional_draw_count
            or request.next_registered_checkpoint is None
        ):
            _fail("query-bound validation execution crossed its request or receipt")
        delta = planning_v2.freeze_v075_query_bound_validation_delta_v2(
            source_model=source_model,
            source_row_id=execution.numerical_row_id,
            signed_validation_batch=append.batch,
            target_validation_draw_count=request.next_registered_checkpoint,
        )
        deltas.append(delta)
    canonical_deltas = tuple(sorted(deltas, key=lambda item: item.source_row_id))
    successor_model = planning_v2.compile_v075_query_bound_validation_overlay_v2(
        source_model=source_model,
        deltas=canonical_deltas,
    )
    successor_proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=successor_model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    return QueryBoundOverlayReplanningV1(
        _RESULT_ISSUER,
        transaction.request.source_operational_trace_id,
        transaction,
        epoch_id,
        source_model,
        source_proof,
        canonical_deltas,
        successor_model,
        successor_proof,
    )


def verify_query_bound_overlay_replanning_bytes_v1(
    *,
    source_trace_bytes: bytes,
    transaction: ground_v1.QueryBoundGroundTransactionV1,
    result_bytes: bytes,
) -> QueryBoundOverlayReplanningV1:
    expected = compile_and_replan_query_bound_ground_transaction_v1(
        source_trace_bytes=source_trace_bytes,
        transaction=transaction,
    )
    if (
        type(result_bytes) is not bytes
        or canonical_json_bytes(loads_canonical_json(result_bytes)) != result_bytes
        or canonical_json_bytes(expected.to_document()) != result_bytes
    ):
        _fail("query-bound overlay replanning bytes differ from exact replay")
    return expected


def verify_query_bound_overlay_replanning_v1(
    claimed: QueryBoundOverlayReplanningV1,
) -> QueryBoundOverlayReplanningV1:
    """Recheck one same-process result before a successor protocol consumes it."""

    if type(claimed) is not QueryBoundOverlayReplanningV1:
        _fail("query-bound overlay replanning result has a foreign type")
    claimed.__post_init__(_RESULT_ISSUER)
    return claimed


__all__ = [
    "ConstructionK7QueryBoundOverlayReplanningV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundOverlayReplanningV1",
    "compile_and_replan_query_bound_ground_transaction_v1",
    "verify_query_bound_overlay_replanning_bytes_v1",
    "verify_query_bound_overlay_replanning_v1",
]
