"""Freeze the final query-local recovery request after transaction-1 replay.

The predecessor is an immutable query-local model and its exact failed proof.
Only frontier rows with one last registered checkpoint are selected.  Rows at
their cap remain explicit and receive no access.  This module accepts no
observer, namespace, signer, kernel, private-law, or ground-tape input.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_overlay_replanning_v1 as replanning_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_VALIDATION_REQUEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.90"
PROFILE_KEY = "construction_k7_query_bound_second_recovery_request_v1"

ROW_REQUEST_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_VALIDATION_REQUEST_V1_DOMAIN
)
REQUEST_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_TRANSACTION_2_RECOVERY_REQUEST_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({ROW_REQUEST_DOMAIN, REQUEST_DOMAIN})
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound transaction-2 request domains are not central")

_ROW_ISSUER = object()
_REQUEST_ISSUER = object()


class ConstructionK7QueryBoundSecondRecoveryRequestV1Error(ValueError):
    """The transaction-1 successor frontier or final local budget changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundSecondRecoveryRequestV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundSecondRecoveryRequestV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class SecondQueryBoundValidationRequestV1:
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
            _fail("transaction-2 validation request is caller-minted")
        _cid(self.numerical_row_id, "transaction-2 numerical row")
        _cid(self.semantic_row_binding_id, "transaction-2 semantic row binding")
        requested = self.disposition == "REQUEST_FINAL_REGISTERED_CHECKPOINT"
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
            _fail("transaction-2 validation request semantics changed")
        object.__setattr__(
            self,
            "_request_id",
            content_id(ROW_REQUEST_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_transaction_2_validation_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "numerical_row_id": self.numerical_row_id,
            "semantic_row_binding_id": self.semantic_row_binding_id,
            "current_validation_draw_count": self.current_validation_draw_count,
            "next_registered_checkpoint": self.next_registered_checkpoint,
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "disposition": self.disposition,
            "selected_from_transaction_1_successor_frontier": True,
            "unmaterialized_successor_count": 0,
            "ground_access_performed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(ROW_REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("transaction-2 validation request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "validation_request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class SecondQueryBoundRecoveryRequestV1:
    _issuer: InitVar[object]
    predecessor_replanning_id: str
    source_operational_trace_id: str
    logical_occurrence_id: str
    reusable_abstract_query_id: str
    source_model_id: str
    source_proof_id: str
    source_frontier_id: str
    rows: tuple[SecondQueryBoundValidationRequestV1, ...]
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER:
            _fail("transaction-2 recovery request is caller-minted")
        for value, label in (
            (self.predecessor_replanning_id, "predecessor replanning"),
            (self.source_operational_trace_id, "source trace"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.reusable_abstract_query_id, "abstract query"),
            (self.source_model_id, "transaction-2 source model"),
            (self.source_proof_id, "transaction-2 source proof"),
            (self.source_frontier_id, "transaction-2 source frontier"),
        ):
            _cid(value, label)
        if (
            type(self.rows) is not tuple
            or not self.rows
            or any(
                type(item) is not SecondQueryBoundValidationRequestV1
                for item in self.rows
            )
            or tuple(item.numerical_row_id for item in self.rows)
            != tuple(sorted({item.numerical_row_id for item in self.rows}))
            or not self.requested_rows
        ):
            _fail("transaction-2 recovery request inventory changed")
        for item in self.rows:
            item.__post_init__(_ROW_ISSUER)
        object.__setattr__(
            self,
            "_request_id",
            content_id(REQUEST_DOMAIN, self._payload()),
        )

    @property
    def requested_rows(self) -> tuple[SecondQueryBoundValidationRequestV1, ...]:
        return tuple(
            item
            for item in self.rows
            if item.disposition == "REQUEST_FINAL_REGISTERED_CHECKPOINT"
        )

    @property
    def cap_blocked_rows(self) -> tuple[SecondQueryBoundValidationRequestV1, ...]:
        return tuple(
            item
            for item in self.rows
            if item.disposition == "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
        )

    @property
    def requested_additional_draw_count(self) -> int:
        return sum(item.requested_additional_draw_count for item in self.rows)

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_transaction_2_recovery_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "predecessor_replanning_id": self.predecessor_replanning_id,
            "source_operational_trace_id": self.source_operational_trace_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "reusable_abstract_query_id": self.reusable_abstract_query_id,
            "source_numerical_model_id": self.source_model_id,
            "source_numerical_proof_id": self.source_proof_id,
            "source_frontier_id": self.source_frontier_id,
            "transaction_index": 2,
            "maximum_local_transactions_per_logical_occurrence": 2,
            "validation_request_ids": [item.request_id for item in self.rows],
            "requested_row_count": len(self.requested_rows),
            "cap_blocked_row_count": len(self.cap_blocked_rows),
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "activation_state": "PREPARED_NO_ACCESS",
            "selection_rule": "ALL_AND_ONLY_SUCCESSOR_FRONTIER_ROWS_WITH_FINAL_REGISTERED_CHECKPOINT",
            "request_frozen_before_transaction_2_namespace_creation": True,
            "cap_blocked_frontier_rows_excluded_and_reported": True,
            "observer_namespace_id": None,
            "observer_input_present": False,
            "signer_input_present": False,
            "kernel_input_present": False,
            "private_law_input_present": False,
            "ground_tape_input_present": False,
            "ground_access_count": 0,
            "ground_execution_authorized": False,
            "next_required_action": "CREATE_TRANSACTION_2_NAMESPACE_AND_EXECUTE_FINAL_LOCAL_ATTEMPT",
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("transaction-2 recovery request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_requests": [item.to_document() for item in self.rows],
            "query_bound_transaction_2_recovery_request_id": self.request_id,
        }


def prepare_second_query_bound_recovery_request_v1(
    predecessor: replanning_v1.QueryBoundOverlayReplanningV1,
) -> SecondQueryBoundRecoveryRequestV1:
    predecessor = replanning_v1.verify_query_bound_overlay_replanning_v1(
        predecessor
    )
    proof = predecessor.successor_proof
    frontier = proof.failed_frontier
    if frontier is None:
        _fail("transaction-2 request requires one exact failed successor proof")
    rows_by_id = {item.row_id: item for item in predecessor.successor_model.rows}
    rows = []
    for obligation in frontier.obligations:
        row = rows_by_id.get(obligation.row_id)
        if row is None or obligation.unmaterialized_successor_ids:
            _fail("transaction-2 frontier row is absent or structurally incomplete")
        next_checkpoint = obligation.next_registered_checkpoint
        requested = (
            0
            if next_checkpoint is None
            else next_checkpoint - obligation.current_validation_draw_count
        )
        rows.append(
            SecondQueryBoundValidationRequestV1(
                _ROW_ISSUER,
                row.row_id,
                row.row_binding_id,
                obligation.current_validation_draw_count,
                next_checkpoint,
                requested,
                (
                    "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
                    if next_checkpoint is None
                    else "REQUEST_FINAL_REGISTERED_CHECKPOINT"
                ),
            )
        )
    return SecondQueryBoundRecoveryRequestV1(
        _REQUEST_ISSUER,
        predecessor.result_id,
        predecessor.source_operational_trace_id,
        predecessor.transaction.request.logical_occurrence_id,
        predecessor.transaction.request.reusable_abstract_query_id,
        predecessor.successor_model.model_id,
        proof.proof_id,
        frontier.frontier_id,
        tuple(sorted(rows, key=lambda item: item.numerical_row_id)),
    )


def verify_second_query_bound_recovery_request_v1(
    claimed: SecondQueryBoundRecoveryRequestV1,
    *,
    predecessor: replanning_v1.QueryBoundOverlayReplanningV1,
) -> SecondQueryBoundRecoveryRequestV1:
    if type(claimed) is not SecondQueryBoundRecoveryRequestV1:
        _fail("transaction-2 recovery request has a foreign type")
    expected = prepare_second_query_bound_recovery_request_v1(predecessor)
    if expected.to_document() != claimed.to_document():
        _fail("transaction-2 recovery request differs from exact replay")
    return expected


__all__ = [
    "ConstructionK7QueryBoundSecondRecoveryRequestV1Error",
    "LOCAL_DOMAINS",
    "SecondQueryBoundRecoveryRequestV1",
    "SecondQueryBoundValidationRequestV1",
    "prepare_second_query_bound_recovery_request_v1",
    "verify_second_query_bound_recovery_request_v1",
]
