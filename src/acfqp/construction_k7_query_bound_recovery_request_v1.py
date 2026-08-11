"""Freeze the minimal next query-local validation request before target access.

The request is derived only after a fresh query has failed on the reusable
root model and then failed again after applying one verified cached recovery
overlay.  It selects exactly the failed-frontier rows that have a registered
next validation checkpoint and reports, but does not execute, cap-blocked
rows.  No namespace, observer, signer, kernel, private law, or ground tape is
accepted here, so the output is a PREPARED_NO_ACCESS request rather than an
acquisition authorization.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_recovery_overlay_v1 as overlay_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_VALIDATION_REQUEST_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.87"
PROFILE_KEY = "construction_k7_query_bound_recovery_request_v1"

ROW_REQUEST_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_VALIDATION_REQUEST_V1_DOMAIN
REQUEST_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_REQUEST_V1_DOMAIN
LOCAL_DOMAINS = frozenset({ROW_REQUEST_DOMAIN, REQUEST_DOMAIN})
if len(LOCAL_DOMAINS) != 2 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound recovery-request domains are not central")

_ROW_ISSUER = object()
_REQUEST_ISSUER = object()


class ConstructionK7QueryBoundRecoveryRequestV1Error(ValueError):
    """The query-bound frontier, checkpoint, or no-access contract changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundRecoveryRequestV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundRecoveryRequestV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class QueryBoundValidationRequestV1:
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
            _fail("query-bound validation request is caller-minted")
        _cid(self.numerical_row_id, "validation numerical row")
        _cid(self.semantic_row_binding_id, "validation semantic row binding")
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
            _fail("query-bound validation request semantics changed")
        object.__setattr__(
            self,
            "_request_id",
            content_id(ROW_REQUEST_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_validation_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "numerical_row_id": self.numerical_row_id,
            "semantic_row_binding_id": self.semantic_row_binding_id,
            "current_validation_draw_count": self.current_validation_draw_count,
            "next_registered_checkpoint": self.next_registered_checkpoint,
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "disposition": self.disposition,
            "selected_from_failed_proof_frontier": True,
            "unmaterialized_successor_count": 0,
            "ground_access_performed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(ROW_REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("query-bound validation request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "validation_request_id": self.request_id}


@dataclass(frozen=True, slots=True)
class QueryBoundRecoveryRequestV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    reusable_build_epoch_envelope_id: str
    reusable_abstract_query_id: str
    root_query_result_id: str
    query_bound_recovery_overlay_id: str
    logical_occurrence_id: str
    overlay_model_epoch_id: str
    overlay_model_id: str
    overlay_proof_id: str
    overlay_frontier_id: str
    transaction_index: int
    rows: tuple[QueryBoundValidationRequestV1, ...]
    _request_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _REQUEST_ISSUER:
            _fail("query-bound recovery request is caller-minted")
        for value, label in (
            (self.source_operational_trace_id, "source trace"),
            (self.reusable_build_epoch_envelope_id, "BuildEpoch envelope"),
            (self.reusable_abstract_query_id, "abstract query"),
            (self.root_query_result_id, "root query result"),
            (self.query_bound_recovery_overlay_id, "recovery overlay"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.overlay_model_epoch_id, "overlay epoch"),
            (self.overlay_model_id, "overlay model"),
            (self.overlay_proof_id, "overlay proof"),
            (self.overlay_frontier_id, "overlay frontier"),
        ):
            _cid(value, label)
        if (
            self.transaction_index != 1
            or type(self.rows) is not tuple
            or not self.rows
            or any(type(item) is not QueryBoundValidationRequestV1 for item in self.rows)
            or tuple(item.numerical_row_id for item in self.rows)
            != tuple(sorted({item.numerical_row_id for item in self.rows}))
            or not self.requested_rows
        ):
            _fail("query-bound recovery request inventory changed")
        for item in self.rows:
            item.__post_init__(_ROW_ISSUER)
        object.__setattr__(
            self,
            "_request_id",
            content_id(REQUEST_DOMAIN, self._payload()),
        )

    @property
    def requested_rows(self) -> tuple[QueryBoundValidationRequestV1, ...]:
        return tuple(
            item
            for item in self.rows
            if item.disposition == "REQUEST_NEXT_REGISTERED_CHECKPOINT"
        )

    @property
    def cap_blocked_rows(self) -> tuple[QueryBoundValidationRequestV1, ...]:
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
            "schema": "acfqp.construction_k7_query_bound_recovery_request.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "reusable_build_epoch_envelope_id": self.reusable_build_epoch_envelope_id,
            "reusable_abstract_query_id": self.reusable_abstract_query_id,
            "root_query_result_id": self.root_query_result_id,
            "query_bound_recovery_overlay_id": self.query_bound_recovery_overlay_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "overlay_model_epoch_id": self.overlay_model_epoch_id,
            "overlay_model_id": self.overlay_model_id,
            "overlay_proof_id": self.overlay_proof_id,
            "overlay_frontier_id": self.overlay_frontier_id,
            "transaction_index": self.transaction_index,
            "validation_request_ids": [item.request_id for item in self.rows],
            "requested_row_count": len(self.requested_rows),
            "cap_blocked_row_count": len(self.cap_blocked_rows),
            "requested_additional_draw_count": self.requested_additional_draw_count,
            "activation_state": "PREPARED_NO_ACCESS",
            "selection_rule": "ALL_AND_ONLY_FRONTIER_ROWS_WITH_NEXT_REGISTERED_CHECKPOINT",
            "request_frozen_before_namespace_creation": True,
            "cap_blocked_frontier_rows_excluded_and_reported": True,
            "observer_namespace_id": None,
            "observer_input_present": False,
            "signer_input_present": False,
            "kernel_input_present": False,
            "private_law_input_present": False,
            "ground_tape_input_present": False,
            "ground_access_count": 0,
            "ground_execution_authorized": False,
            "next_required_action": "CREATE_QUERY_BOUND_NAMESPACE_AND_REVERIFY_REQUEST",
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def request_id(self) -> str:
        current = content_id(REQUEST_DOMAIN, self._payload())
        if current != self._request_id:
            _fail("query-bound recovery request changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "validation_requests": [item.to_document() for item in self.rows],
            "query_bound_recovery_request_id": self.request_id,
        }


def prepare_query_bound_recovery_request_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
    overlay_bytes: bytes,
) -> QueryBoundRecoveryRequestV1:
    overlay = overlay_v1.verify_query_bound_cached_recovery_overlay_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        root_query_result_bytes=root_query_result_bytes,
        overlay_bytes=overlay_bytes,
    )
    root_result = query_v1.verify_reusable_abstract_query_result_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        result_bytes=root_query_result_bytes,
    )
    trace = loads_canonical_json(source_trace_bytes)
    try:
        final_epoch = trace["causal_recovery_chain"]["final_model_epoch"]
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(final_epoch["model"])
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(final_epoch["proof"])
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundRecoveryRequestV1Error(
            "query-bound recovery request lacks one exact final epoch"
        ) from error
    frontier = proof.failed_frontier
    if (
        root_result.query.query_id != overlay.reusable_abstract_query_id
        or root_result.result_id != overlay.root_query_result_id
        or model.model_id != overlay.overlay_model_id
        or proof.proof_id != overlay.overlay_proof_id
        or frontier is None
        or frontier.frontier_id != overlay.overlay_frontier_id
        or proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
    ):
        _fail("query-bound recovery request crossed its query or overlay proof")
    rows_by_id = {item.row_id: item for item in model.rows}
    if len(rows_by_id) != len(model.rows):
        _fail("query-bound overlay model contains duplicate rows")
    requests: list[QueryBoundValidationRequestV1] = []
    for obligation in frontier.obligations:
        row = rows_by_id.get(obligation.row_id)
        if row is None or obligation.unmaterialized_successor_ids:
            _fail("query-bound frontier is not validation-only")
        checkpoint = obligation.next_registered_checkpoint
        requests.append(
            QueryBoundValidationRequestV1(
                _ROW_ISSUER,
                row.row_id,
                row.row_binding_id,
                obligation.current_validation_draw_count,
                checkpoint,
                0 if checkpoint is None else checkpoint - obligation.current_validation_draw_count,
                (
                    "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT"
                    if checkpoint is None
                    else "REQUEST_NEXT_REGISTERED_CHECKPOINT"
                ),
            )
        )
    return QueryBoundRecoveryRequestV1(
        _REQUEST_ISSUER,
        overlay.source_operational_trace_id,
        overlay.reusable_build_epoch_envelope_id,
        overlay.reusable_abstract_query_id,
        overlay.root_query_result_id,
        overlay.overlay_id,
        overlay.logical_occurrence_id,
        overlay.overlay_model_epoch_id,
        overlay.overlay_model_id,
        overlay.overlay_proof_id,
        overlay.overlay_frontier_id,
        1,
        tuple(sorted(requests, key=lambda item: item.numerical_row_id)),
    )


def verify_query_bound_recovery_request_bytes_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
    overlay_bytes: bytes,
    request_bytes: bytes,
) -> QueryBoundRecoveryRequestV1:
    if type(request_bytes) is not bytes or not request_bytes:
        _fail("query-bound recovery request must be nonempty bytes")
    try:
        document = loads_canonical_json(request_bytes)
    except Exception as error:
        raise ConstructionK7QueryBoundRecoveryRequestV1Error(
            "query-bound recovery request is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != request_bytes:
        _fail("query-bound recovery request is not one canonical object")
    expected = prepare_query_bound_recovery_request_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        root_query_result_bytes=root_query_result_bytes,
        overlay_bytes=overlay_bytes,
    )
    if canonical_json_bytes(expected.to_document()) != request_bytes:
        _fail("query-bound recovery request differs from exact replay")
    return expected


def require_query_bound_recovery_request_v1(
    claimed: QueryBoundRecoveryRequestV1,
) -> QueryBoundRecoveryRequestV1:
    """Revalidate one exact issuer-minted in-process request."""

    if type(claimed) is not QueryBoundRecoveryRequestV1:
        _fail("query-bound recovery request has a foreign type")
    claimed.__post_init__(_REQUEST_ISSUER)
    return claimed


__all__ = [
    "ConstructionK7QueryBoundRecoveryRequestV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundRecoveryRequestV1",
    "QueryBoundValidationRequestV1",
    "prepare_query_bound_recovery_request_v1",
    "require_query_bound_recovery_request_v1",
    "verify_query_bound_recovery_request_bytes_v1",
]
