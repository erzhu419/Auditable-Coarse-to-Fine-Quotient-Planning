"""Apply a verified cached recovery overlay only after one query proof fails.

The query first runs against the reusable root BuildEpoch through the public
ground-free query boundary.  This module accepts that exact failed result and
the source occurrence's verified causal-recovery trace, then activates the
immutable successor model as a cached overlay and replans the same H=2 query.

No observer, signer, kernel, private law, ground tape, or new acquisition input
is accepted.  Consequently this is a legitimate reuse path, not a fresh-query
ground-recovery transaction.  If the successor proof still fails, a later
query-bound observer/namespace handoff remains necessary.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_causal_recovery_chain_v1 as recovery_v1
from acfqp import construction_k7_reusable_abstract_query_v1 as query_v1
from acfqp import construction_k7_reusable_build_epoch_authority_v1 as build_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_OVERLAY_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.86"
PROFILE_KEY = "construction_k7_query_bound_recovery_overlay_v1"

OVERLAY_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_RECOVERY_OVERLAY_V1_DOMAIN
LOCAL_DOMAINS = frozenset({OVERLAY_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound recovery overlay domain is not central")

_OVERLAY_ISSUER = object()


class ConstructionK7QueryBoundRecoveryOverlayV1Error(ValueError):
    """The query failure, cached lineage, or successor replanning changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundRecoveryOverlayV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundRecoveryOverlayV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class QueryBoundRecoveryOverlayV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    reusable_build_epoch_envelope_id: str
    reusable_abstract_query_id: str
    root_query_result_id: str
    logical_occurrence_id: str
    root_model_id: str
    root_proof_id: str
    root_frontier_id: str
    causal_recovery_chain_replay_id: str
    overlay_model_epoch_id: str
    overlay_model_id: str
    overlay_proof_id: str
    overlay_frontier_id: str | None
    root_row_count: int
    overlay_row_count: int
    introduced_row_count: int
    preserved_root_row_count: int
    updated_root_row_count: int
    _overlay_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _OVERLAY_ISSUER:
            _fail("query-bound recovery overlay is caller-minted")
        for value, label in (
            (self.source_operational_trace_id, "source trace"),
            (self.reusable_build_epoch_envelope_id, "BuildEpoch envelope"),
            (self.reusable_abstract_query_id, "abstract query"),
            (self.root_query_result_id, "root query result"),
            (self.logical_occurrence_id, "logical occurrence"),
            (self.root_model_id, "root model"),
            (self.root_proof_id, "root proof"),
            (self.root_frontier_id, "root frontier"),
            (self.causal_recovery_chain_replay_id, "recovery replay"),
            (self.overlay_model_epoch_id, "overlay epoch"),
            (self.overlay_model_id, "overlay model"),
            (self.overlay_proof_id, "overlay proof"),
        ):
            _cid(value, label)
        if self.overlay_frontier_id is not None:
            _cid(self.overlay_frontier_id, "overlay frontier")
        if (
            type(self.root_row_count) is not int
            or self.root_row_count <= 0
            or type(self.overlay_row_count) is not int
            or self.overlay_row_count <= self.root_row_count
            or type(self.introduced_row_count) is not int
            or self.introduced_row_count
            != self.overlay_row_count - self.root_row_count
            or type(self.preserved_root_row_count) is not int
            or self.preserved_root_row_count < 0
            or type(self.updated_root_row_count) is not int
            or self.updated_root_row_count < 0
            or self.preserved_root_row_count + self.updated_root_row_count
            != self.root_row_count
        ):
            _fail("query-bound recovery overlay row counts changed")
        object.__setattr__(
            self,
            "_overlay_id",
            content_id(OVERLAY_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        failed = self.overlay_frontier_id is not None
        return {
            "schema": "acfqp.construction_k7_query_bound_recovery_overlay.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "reusable_build_epoch_envelope_id": self.reusable_build_epoch_envelope_id,
            "reusable_abstract_query_id": self.reusable_abstract_query_id,
            "root_query_result_id": self.root_query_result_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "root_model_id": self.root_model_id,
            "root_proof_id": self.root_proof_id,
            "root_frontier_id": self.root_frontier_id,
            "causal_recovery_chain_replay_id": self.causal_recovery_chain_replay_id,
            "overlay_model_epoch_id": self.overlay_model_epoch_id,
            "overlay_model_id": self.overlay_model_id,
            "overlay_proof_id": self.overlay_proof_id,
            "overlay_frontier_id": self.overlay_frontier_id,
            "root_row_count": self.root_row_count,
            "overlay_row_count": self.overlay_row_count,
            "introduced_row_count": self.introduced_row_count,
            "preserved_root_row_count": self.preserved_root_row_count,
            "updated_root_row_count": self.updated_root_row_count,
            "activation_condition": "CURRENT_QUERY_EXACT_ROOT_PROOF_FAILED",
            "ground_distinction_restore_mode": "VERIFIED_CACHED_OVERLAY",
            "root_row_bindings_strictly_extended": True,
            "changed_root_rows_retain_their_semantic_binding": True,
            "root_failure_verified_before_overlay_activation": True,
            "cached_overlay_lineage_exactly_replayed": True,
            "post_overlay_replanning_exactly_recomputed": True,
            "model_construction_repeated": False,
            "new_ground_access_count": 0,
            "observer_input_present": False,
            "signer_input_present": False,
            "private_law_input_present": False,
            "kernel_input_present": False,
            "fresh_query_ground_recovery_executed": False,
            "fresh_query_observer_namespace_handoff_present": False,
            "next_ground_transaction_required": failed,
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def overlay_id(self) -> str:
        current = content_id(OVERLAY_DOMAIN, self._payload())
        if current != self._overlay_id:
            _fail("query-bound recovery overlay changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "query_bound_recovery_overlay_id": self.overlay_id}


def apply_query_bound_cached_recovery_overlay_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
) -> QueryBoundRecoveryOverlayV1:
    build_epoch = build_v1.verify_reusable_build_epoch_authority_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        envelope_bytes=build_epoch_envelope_bytes,
    )
    root_result = query_v1.verify_reusable_abstract_query_result_bytes_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        result_bytes=root_query_result_bytes,
    )
    root_proof = root_result.numerical_proof
    root_frontier = root_proof.failed_frontier
    if (
        root_proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        or root_frontier is None
        or root_result.source_operational_trace_id
        != build_epoch.source_operational_trace_id
    ):
        _fail("cached overlay requires the current query's exact failed proof")
    recovery = recovery_v1.replay_construction_k7_causal_recovery_chain_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
    )
    if (
        recovery.source_operational_trace_id
        != build_epoch.source_operational_trace_id
        or recovery.root_model_epoch_id != build_epoch.root_model_epoch_id
        or recovery.root_proof_id != root_proof.proof_id
        or recovery.root_frontier_id != root_frontier.frontier_id
    ):
        _fail("cached recovery lineage crossed the current query failure")
    trace = loads_canonical_json(source_trace_bytes)
    try:
        chain = trace["causal_recovery_chain"]
        final_epoch_document = chain["final_model_epoch"]
        final_model_document = final_epoch_document["model"]
        final_proof_document = final_epoch_document["proof"]
    except (KeyError, TypeError) as error:
        raise ConstructionK7QueryBoundRecoveryOverlayV1Error(
            "cached recovery successor model is absent"
        ) from error
    final_model = planning_v2.replay_v075_numerical_model_bytes_v2(
        canonical_json_bytes(final_model_document)
    )
    final_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
        canonical_json_bytes(final_proof_document)
    )
    replanned = planning_v2.plan_v075_construction_numerical_model_v2(
        model=final_model,
        route=root_result.query.route,
    )
    if (
        replanned.canonical_bytes != final_proof.canonical_bytes
        or chain["final_model_epoch_id"] != recovery.final_model_epoch_id
        or chain["final_numerical_model_id"] != final_model.model_id
        or chain["final_proof_id"] != final_proof.proof_id
        or final_epoch_document["model_epoch_id"] != recovery.final_model_epoch_id
        or root_proof.model.context.context_id != final_model.context.context_id
    ):
        _fail("cached overlay successor proof differs from exact replanning")
    root_rows = {row.row_binding_id: row.row_id for row in root_proof.model.rows}
    overlay_rows = {row.row_binding_id: row.row_id for row in final_model.rows}
    if (
        len(root_rows) != len(root_proof.model.rows)
        or len(overlay_rows) != len(final_model.rows)
        or not set(root_rows) < set(overlay_rows)
    ):
        _fail("cached overlay is not a strict semantic-row extension")
    preserved_root_rows = {
        binding_id
        for binding_id, row_id in root_rows.items()
        if overlay_rows[binding_id] == row_id
    }
    updated_root_rows = set(root_rows) - preserved_root_rows
    overlay_frontier = final_proof.failed_frontier
    return QueryBoundRecoveryOverlayV1(
        _OVERLAY_ISSUER,
        build_epoch.source_operational_trace_id,
        build_epoch.envelope_id,
        root_result.query.query_id,
        root_result.result_id,
        root_result.query.logical_occurrence_id,
        root_proof.model.model_id,
        root_proof.proof_id,
        root_frontier.frontier_id,
        recovery.result_id,
        recovery.final_model_epoch_id,
        final_model.model_id,
        final_proof.proof_id,
        None if overlay_frontier is None else overlay_frontier.frontier_id,
        len(root_rows),
        len(overlay_rows),
        len(set(overlay_rows) - set(root_rows)),
        len(preserved_root_rows),
        len(updated_root_rows),
    )


def verify_query_bound_cached_recovery_overlay_bytes_v1(
    *,
    source_trace_bytes: bytes,
    build_epoch_envelope_bytes: bytes,
    root_query_result_bytes: bytes,
    overlay_bytes: bytes,
) -> QueryBoundRecoveryOverlayV1:
    expected = apply_query_bound_cached_recovery_overlay_v1(
        source_trace_bytes=source_trace_bytes,
        build_epoch_envelope_bytes=build_epoch_envelope_bytes,
        root_query_result_bytes=root_query_result_bytes,
    )
    if (
        type(overlay_bytes) is not bytes
        or canonical_json_bytes(loads_canonical_json(overlay_bytes)) != overlay_bytes
        or canonical_json_bytes(expected.to_document()) != overlay_bytes
    ):
        _fail("query-bound cached overlay differs from exact replay")
    return expected


__all__ = [
    "ConstructionK7QueryBoundRecoveryOverlayV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundRecoveryOverlayV1",
    "apply_query_bound_cached_recovery_overlay_v1",
    "verify_query_bound_cached_recovery_overlay_bytes_v1",
]
