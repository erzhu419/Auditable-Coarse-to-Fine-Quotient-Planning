"""Freeze and reuse the query-neutral RAPM produced by local recovery.

The source occurrence has already exhausted its two registered local ground
transactions.  Its final immutable numerical model is exported as portable
bytes and may then serve a fresh logical occurrence.  The fresh-query entry
accepts no observer, signer, kernel, ground tape, or acquisition schedule: it
reconstructs the model and performs the H=2 abstract search from the snapshot.

This slice deliberately does not claim that the source acquisition lineage is
independently replayable from the snapshot alone.  That join remains a later
bundle-level authority.  It also does not issue a plan certificate when the
reused model still exposes a failed proof frontier.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_final_local_replanning_v1 as final_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.106"
PROFILE_KEY = "construction_k7_query_bound_reusable_rapm_snapshot_v1"

SNAPSHOT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN
QUERY_SPEC_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN
QUERY_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset(
    {SNAPSHOT_DOMAIN, QUERY_SPEC_DOMAIN, QUERY_RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 3 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("query-bound reusable RAPM domains are not central")

_SNAPSHOT_ISSUER = object()
_QUERY_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(ValueError):
    """The recovered model, source lineage, or fresh query diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _positive(value: Any, label: str) -> int:
    if type(value) is not int or value <= 0:
        _fail(f"{label} must be one positive integer")
    return value


@dataclass(frozen=True, slots=True)
class QueryBoundReusableRAPMSnapshotV1:
    _issuer: InitVar[object]
    source_operational_trace_id: str
    source_logical_occurrence_id: str
    source_reusable_abstract_query_id: str
    source_final_local_replanning_id: str
    transaction_1_replanning_id: str
    transaction_2_recovery_request_id: str
    transaction_2_ground_transaction_id: str
    source_numerical_model_id: str
    source_numerical_proof_id: str
    source_frontier_id: str
    reusable_model: planning_v2.V075NumericalModelV2 = field(repr=False)
    reusable_proof: planning_v2.V075NumericalPlanningProofV2 = field(
        repr=False
    )
    changed_row_binding_ids: tuple[str, ...]
    preserved_row_binding_ids: tuple[str, ...]
    source_validation_draw_count_on_changed_rows: int
    added_signed_validation_draw_count: int
    reusable_validation_draw_count_on_changed_rows: int
    cumulative_local_ground_draw_count: int
    _snapshot_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SNAPSHOT_ISSUER
            or type(self.reusable_model) is not planning_v2.V075NumericalModelV2
            or type(self.reusable_proof)
            is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("reusable RAPM snapshot is caller-minted")
        for value, label in (
            (self.source_operational_trace_id, "source operational trace"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.source_reusable_abstract_query_id, "source abstract query"),
            (self.source_final_local_replanning_id, "source final replanning"),
            (self.transaction_1_replanning_id, "transaction-1 replanning"),
            (self.transaction_2_recovery_request_id, "transaction-2 request"),
            (self.transaction_2_ground_transaction_id, "transaction-2 result"),
            (self.source_numerical_model_id, "source numerical model"),
            (self.source_numerical_proof_id, "source numerical proof"),
            (self.source_frontier_id, "source failed frontier"),
        ):
            _cid(value, label)
        changed = self.changed_row_binding_ids
        preserved = self.preserved_row_binding_ids
        if (
            type(changed) is not tuple
            or type(preserved) is not tuple
            or changed != tuple(sorted(set(changed)))
            or preserved != tuple(sorted(set(preserved)))
            or not changed
            or set(changed).intersection(preserved)
            or any(type(item) is not str for item in (*changed, *preserved))
        ):
            _fail("reusable RAPM semantic-row partition changed")
        row_bindings = tuple(
            sorted(item.row_binding_id for item in self.reusable_model.rows)
        )
        if (
            tuple(sorted((*changed, *preserved))) != row_bindings
            or self.reusable_proof.model != self.reusable_model
            or self.reusable_proof.route
            is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or self.reusable_proof.outcome
            is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
            or self.reusable_proof.failed_frontier is None
        ):
            _fail("reusable RAPM model/proof closure changed")
        source_draws = _positive(
            self.source_validation_draw_count_on_changed_rows,
            "source validation draws",
        )
        added_draws = _positive(
            self.added_signed_validation_draw_count,
            "added validation draws",
        )
        reusable_draws = _positive(
            self.reusable_validation_draw_count_on_changed_rows,
            "reusable validation draws",
        )
        _positive(
            self.cumulative_local_ground_draw_count,
            "cumulative local ground draws",
        )
        if source_draws + added_draws != reusable_draws:
            _fail("reusable RAPM validation-draw accounting changed")
        model_document = self.reusable_model.to_document()
        proof_document = self.reusable_proof.to_document()
        if (
            model_document["occurrence_or_arm_fields_present"] is not False
            or model_document["prior_or_proposal_fields_present"] is not False
            or model_document["private_law_access"] is not False
            or proof_document["occurrence_field_present"] is not False
            or proof_document["source_provenance_field_present"] is not False
            or proof_document["private_law_access"] is not False
        ):
            _fail("reusable RAPM retained query-local or private authority")
        object.__setattr__(
            self,
            "_snapshot_id",
            content_id(SNAPSHOT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.reusable_proof.failed_frontier
        return {
            "schema": "acfqp.construction_k7_query_bound_reusable_rapm_snapshot.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_operational_trace_id": self.source_operational_trace_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "source_reusable_abstract_query_id": self.source_reusable_abstract_query_id,
            "source_final_local_replanning_id": self.source_final_local_replanning_id,
            "transaction_1_replanning_id": self.transaction_1_replanning_id,
            "transaction_2_recovery_request_id": self.transaction_2_recovery_request_id,
            "transaction_2_ground_transaction_id": self.transaction_2_ground_transaction_id,
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_numerical_proof_id": self.source_numerical_proof_id,
            "source_frontier_id": self.source_frontier_id,
            "reusable_numerical_model_id": self.reusable_model.model_id,
            "reusable_numerical_proof_id": self.reusable_proof.proof_id,
            "reusable_frontier_id": frontier.frontier_id,
            "changed_semantic_row_binding_ids": list(
                self.changed_row_binding_ids
            ),
            "preserved_semantic_row_binding_ids": list(
                self.preserved_row_binding_ids
            ),
            "reusable_row_count": len(self.reusable_model.rows),
            "changed_row_count": len(self.changed_row_binding_ids),
            "preserved_row_count": len(self.preserved_row_binding_ids),
            "source_validation_draw_count_on_changed_rows": (
                self.source_validation_draw_count_on_changed_rows
            ),
            "added_signed_validation_draw_count": (
                self.added_signed_validation_draw_count
            ),
            "reusable_validation_draw_count_on_changed_rows": (
                self.reusable_validation_draw_count_on_changed_rows
            ),
            "cumulative_local_ground_draw_count": (
                self.cumulative_local_ground_draw_count
            ),
            "source_local_transaction_count": 2,
            "query_neutral_numerical_model_present": True,
            "portable_exact_replanning_proof_present": True,
            "query_provenance_projected_out_of_model": True,
            "source_occurrence_bundle_binding_present": False,
            "portable_source_ground_transaction_replay_present": False,
            "fresh_query_ground_access_authority_present": False,
            "persistent_proof_dependency_dag_present": False,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
            "next_required_action": (
                "BIND_SNAPSHOT_TO_SOURCE_OCCURRENCE_BUNDLE_AND_FRESH_QUERY"
            ),
        }

    @property
    def snapshot_id(self) -> str:
        current = content_id(SNAPSHOT_DOMAIN, self._payload())
        if current != self._snapshot_id:
            _fail("reusable RAPM snapshot changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "reusable_model": self.reusable_model.to_document(),
            "reusable_proof": self.reusable_proof.to_document(),
            "query_bound_reusable_rapm_snapshot_id": self.snapshot_id,
        }


@dataclass(frozen=True, slots=True)
class QueryBoundReusableRAPMQuerySpecV1:
    _issuer: InitVar[object]
    reusable_rapm_snapshot_id: str
    reusable_numerical_model_id: str
    source_logical_occurrence_id: str
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    route: planning_v2.V075PlanningRouteV2
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("reusable RAPM query is caller-minted")
        for value, label in (
            (self.reusable_rapm_snapshot_id, "reusable RAPM snapshot"),
            (self.reusable_numerical_model_id, "reusable numerical model"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.logical_occurrence_id, "fresh logical occurrence"),
            (self.threshold_profile_id, "threshold profile"),
        ):
            _cid(value, label)
        try:
            route = planning_v2.V075PlanningRouteV2(self.route)
        except (TypeError, ValueError) as error:
            raise ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(
                "reusable RAPM query route changed"
            ) from error
        object.__setattr__(self, "route", route)
        expected_threshold = worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        if (
            self.source_logical_occurrence_id == self.logical_occurrence_id
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 0
            or self.threshold_profile_id != expected_threshold
            or route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        ):
            _fail("reusable RAPM fresh-query identity changed")
        object.__setattr__(
            self,
            "_query_id",
            content_id(QUERY_SPEC_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_reusable_rapm_query_spec.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "reusable_rapm_snapshot_id": self.reusable_rapm_snapshot_id,
            "reusable_numerical_model_id": self.reusable_numerical_model_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "route": self.route.value,
            "fresh_logical_occurrence": True,
            "ground_input_parameter_present": False,
            "observer_or_signer_input_present": False,
            "model_construction_repeated": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_SPEC_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("reusable RAPM query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_reusable_rapm_query_id": self.query_id,
        }


@dataclass(frozen=True, slots=True)
class QueryBoundReusableRAPMQueryResultV1:
    _issuer: InitVar[object]
    query: QueryBoundReusableRAPMQuerySpecV1
    proof: planning_v2.V075NumericalPlanningProofV2 = field(repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.query) is not QueryBoundReusableRAPMQuerySpecV1
            or type(self.proof) is not planning_v2.V075NumericalPlanningProofV2
        ):
            _fail("reusable RAPM query result is caller-minted")
        self.query.__post_init__(_QUERY_ISSUER)
        if (
            self.proof.model.model_id != self.query.reusable_numerical_model_id
            or self.proof.route is not self.query.route
        ):
            _fail("reusable RAPM query proof crossed its model or route")
        object.__setattr__(
            self,
            "_result_id",
            content_id(QUERY_RESULT_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.proof.failed_frontier
        policy = self.proof.policy
        return {
            "schema": "acfqp.construction_k7_query_bound_reusable_rapm_query_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "reusable_rapm_snapshot_id": self.query.reusable_rapm_snapshot_id,
            "reusable_rapm_query_id": self.query.query_id,
            "source_logical_occurrence_id": self.query.source_logical_occurrence_id,
            "logical_occurrence_id": self.query.logical_occurrence_id,
            "reusable_numerical_model_id": self.query.reusable_numerical_model_id,
            "numerical_proof_id": self.proof.proof_id,
            "numerical_outcome": self.proof.outcome.value,
            "policy_id": None if policy is None else policy.policy_id,
            "failed_frontier_id": None if frontier is None else frontier.frontier_id,
            "fresh_logical_occurrence": True,
            "snapshot_model_reused": True,
            "model_construction_repeated": False,
            "new_ground_access_count": 0,
            "ground_input_parameter_present": False,
            "observer_or_signer_input_present": False,
            "exact_abstract_replanning_completed": True,
            "certificate_failed_frontier_present": frontier is not None,
            "query_local_ground_recovery_authorized_here": False,
            "query_local_ground_recovery_executed_here": False,
            "plan_certificate_issued": False,
            "campaign_closure_issued": False,
            "official_execution_allowed": False,
            "next_required_action": (
                "QUERY_LOCAL_CERTIFICATE_FRONTIER_RESOLUTION"
                if frontier is not None
                else "INDEPENDENT_PLAN_CERTIFICATE_AUDIT"
            ),
        }

    @property
    def result_id(self) -> str:
        current = content_id(QUERY_RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("reusable RAPM query result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query": self.query.to_document(),
            "numerical_proof": self.proof.to_document(),
            "query_bound_reusable_rapm_query_result_id": self.result_id,
        }


def freeze_query_bound_reusable_rapm_snapshot_v1(
    final_local: final_v1.QueryBoundFinalLocalReplanningV1,
) -> QueryBoundReusableRAPMSnapshotV1:
    final_local = final_v1.verify_query_bound_final_local_replanning_v1(
        final_local
    )
    source_frontier = final_local.source_proof.failed_frontier
    if source_frontier is None:
        _fail("reusable RAPM source proof has no failed frontier")
    document = final_local.to_document()
    return QueryBoundReusableRAPMSnapshotV1(
        _SNAPSHOT_ISSUER,
        document["source_operational_trace_id"],
        document["logical_occurrence_id"],
        document["reusable_abstract_query_id"],
        final_local.result_id,
        document["transaction_1_replanning_id"],
        document["transaction_2_recovery_request_id"],
        document["transaction_2_ground_transaction_id"],
        final_local.source_model.model_id,
        final_local.source_proof.proof_id,
        source_frontier.frontier_id,
        final_local.successor_model,
        final_local.successor_proof,
        final_local.changed_row_binding_ids,
        final_local.preserved_row_binding_ids,
        document["source_validation_draw_count_on_changed_rows"],
        document["added_signed_validation_draw_count"],
        document["successor_validation_draw_count_on_changed_rows"],
        document["cumulative_local_ground_draw_count"],
    )


def require_query_bound_reusable_rapm_snapshot_v1(
    snapshot: QueryBoundReusableRAPMSnapshotV1,
) -> QueryBoundReusableRAPMSnapshotV1:
    if type(snapshot) is not QueryBoundReusableRAPMSnapshotV1:
        _fail("reusable RAPM snapshot has a foreign type")
    snapshot.__post_init__(_SNAPSHOT_ISSUER)
    return snapshot


def replay_query_bound_reusable_rapm_snapshot_bytes_v1(
    snapshot_bytes: bytes,
) -> QueryBoundReusableRAPMSnapshotV1:
    if type(snapshot_bytes) is not bytes or not snapshot_bytes:
        _fail("reusable RAPM snapshot must be nonempty bytes")
    try:
        document = loads_canonical_json(snapshot_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != snapshot_bytes:
            _fail("reusable RAPM snapshot is not one canonical object")
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(document["reusable_model"])
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(document["reusable_proof"])
        )
        snapshot = QueryBoundReusableRAPMSnapshotV1(
            _SNAPSHOT_ISSUER,
            document["source_operational_trace_id"],
            document["source_logical_occurrence_id"],
            document["source_reusable_abstract_query_id"],
            document["source_final_local_replanning_id"],
            document["transaction_1_replanning_id"],
            document["transaction_2_recovery_request_id"],
            document["transaction_2_ground_transaction_id"],
            document["source_numerical_model_id"],
            document["source_numerical_proof_id"],
            document["source_frontier_id"],
            model,
            proof,
            tuple(document["changed_semantic_row_binding_ids"]),
            tuple(document["preserved_semantic_row_binding_ids"]),
            document["source_validation_draw_count_on_changed_rows"],
            document["added_signed_validation_draw_count"],
            document["reusable_validation_draw_count_on_changed_rows"],
            document["cumulative_local_ground_draw_count"],
        )
    except ConstructionK7QueryBoundReusableRAPMSnapshotV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(
            "reusable RAPM snapshot failed typed replay"
        ) from error
    if canonical_json_bytes(snapshot.to_document()) != snapshot_bytes:
        _fail("reusable RAPM snapshot differs from exact replay")
    return snapshot


def freeze_query_bound_reusable_rapm_query_spec_v1(
    *,
    snapshot: QueryBoundReusableRAPMSnapshotV1,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> QueryBoundReusableRAPMQuerySpecV1:
    snapshot = require_query_bound_reusable_rapm_snapshot_v1(snapshot)
    return QueryBoundReusableRAPMQuerySpecV1(
        _QUERY_ISSUER,
        snapshot.snapshot_id,
        snapshot.reusable_model.model_id,
        snapshot.source_logical_occurrence_id,
        _cid(logical_occurrence_id, "fresh logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
        planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )


def run_query_bound_reusable_rapm_query_v1(
    *,
    snapshot_bytes: bytes,
    query: QueryBoundReusableRAPMQuerySpecV1,
) -> QueryBoundReusableRAPMQueryResultV1:
    snapshot = replay_query_bound_reusable_rapm_snapshot_bytes_v1(
        snapshot_bytes
    )
    if type(query) is not QueryBoundReusableRAPMQuerySpecV1:
        _fail("reusable RAPM query has a foreign type")
    query.__post_init__(_QUERY_ISSUER)
    if (
        query.reusable_rapm_snapshot_id != snapshot.snapshot_id
        or query.reusable_numerical_model_id != snapshot.reusable_model.model_id
        or query.source_logical_occurrence_id
        != snapshot.source_logical_occurrence_id
    ):
        _fail("reusable RAPM query crossed its snapshot")
    proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=snapshot.reusable_model,
        route=query.route,
    )
    return QueryBoundReusableRAPMQueryResultV1(
        _RESULT_ISSUER,
        query,
        proof,
    )


def verify_query_bound_reusable_rapm_query_result_bytes_v1(
    *,
    snapshot_bytes: bytes,
    result_bytes: bytes,
) -> QueryBoundReusableRAPMQueryResultV1:
    if type(result_bytes) is not bytes or not result_bytes:
        _fail("reusable RAPM query result must be nonempty bytes")
    try:
        document = loads_canonical_json(result_bytes)
        if type(document) is not dict or canonical_json_bytes(document) != result_bytes:
            _fail("reusable RAPM query result is not canonical")
        snapshot = replay_query_bound_reusable_rapm_snapshot_bytes_v1(
            snapshot_bytes
        )
        query_document = document["query"]
        query = QueryBoundReusableRAPMQuerySpecV1(
            _QUERY_ISSUER,
            query_document["reusable_rapm_snapshot_id"],
            query_document["reusable_numerical_model_id"],
            query_document["source_logical_occurrence_id"],
            query_document["logical_occurrence_id"],
            query_document["query_ordinal"],
            query_document["threshold_profile_id"],
            planning_v2.V075PlanningRouteV2(query_document["route"]),
        )
        if query.reusable_rapm_snapshot_id != snapshot.snapshot_id:
            _fail("reusable RAPM query result crossed its snapshot")
        expected = run_query_bound_reusable_rapm_query_v1(
            snapshot_bytes=snapshot_bytes,
            query=query,
        )
    except ConstructionK7QueryBoundReusableRAPMSnapshotV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSnapshotV1Error(
            "reusable RAPM query result failed typed replay"
        ) from error
    if canonical_json_bytes(expected.to_document()) != result_bytes:
        _fail("reusable RAPM query result differs from exact replanning")
    return expected


__all__ = [
    "ConstructionK7QueryBoundReusableRAPMSnapshotV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundReusableRAPMQueryResultV1",
    "QueryBoundReusableRAPMQuerySpecV1",
    "QueryBoundReusableRAPMSnapshotV1",
    "freeze_query_bound_reusable_rapm_query_spec_v1",
    "freeze_query_bound_reusable_rapm_snapshot_v1",
    "replay_query_bound_reusable_rapm_snapshot_bytes_v1",
    "require_query_bound_reusable_rapm_snapshot_v1",
    "run_query_bound_reusable_rapm_query_v1",
    "verify_query_bound_reusable_rapm_query_result_bytes_v1",
]
