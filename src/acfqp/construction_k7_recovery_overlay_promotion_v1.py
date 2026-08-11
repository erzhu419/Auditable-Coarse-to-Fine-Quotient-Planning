"""Promote one recovered RAPM overlay for exact reuse by a later query.

The source recovery loop has already paid for six query-local validation
increments and compiled them into a query-neutral numerical model.  This
module freezes that successor model/proof pair as a new immutable epoch, binds
one fresh occurrence to it, and replays the cached failed proof before any
new planner or ground access.

The registered fixture reaches the validation cap on all seven frontier rows.
Consequently the later occurrence is routed directly to its own identity-
bound ground fallback with zero repeated local-recovery draws.  This is a
cross-query reuse and sample-tax result, not an abstract plan certificate or
an official economics claim.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
from typing import Any, NoReturn

from acfqp import construction_k7_recovery_eligible_world_model_loop_v1 as loop_v1
from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.113"
PROFILE_KEY = "construction_k7_recovery_overlay_promotion_v1"

EPOCH_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN
CONSUMPTION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN
LOCAL_DOMAINS = frozenset(
    {EPOCH_DOMAIN, QUERY_DOMAIN, CONSUMPTION_DOMAIN, RESULT_DOMAIN}
)
if len(LOCAL_DOMAINS) != 4 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("recovery-overlay promotion domains are not central")

_EPOCH_ISSUER = object()
_QUERY_ISSUER = object()
_CONSUMPTION_ISSUER = object()
_RESULT_ISSUER = object()


class ConstructionK7RecoveryOverlayPromotionV1Error(ValueError):
    """The promoted overlay, fresh query, or reuse accounting changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryOverlayPromotionV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryOverlayPromotionV1Error(
            f"{label} must be one exact content ID"
        ) from error


@dataclass(frozen=True, slots=True)
class RecoveryOverlayPromotedEpochV1:
    _issuer: InitVar[object]
    source_loop: loop_v1.RecoveryEligibleWorldModelLoopV1 = field(repr=False)
    _epoch_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _EPOCH_ISSUER
            or type(self.source_loop) is not loop_v1.RecoveryEligibleWorldModelLoopV1
        ):
            _fail("promoted RAPM epoch is caller-minted")
        loop_v1.require_recovery_eligible_world_model_loop_v1(self.source_loop)
        model = self.source_loop.successor_model
        proof = self.source_loop.successor_proof
        frontier = proof.failed_frontier
        model_document = model.to_document()
        proof_document = proof.to_document()
        if (
            proof.model != model
            or proof.route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
            or proof.outcome is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
            or frontier is None
            or len(model.rows) != 18
            or len(frontier.obligations) != 7
            or any(
                item.next_registered_checkpoint is not None
                for item in frontier.obligations
            )
            or self.source_loop.transaction.total_ground_draw_count != 12_672
            or self.source_loop.added_validation_draw_count != 12_288
            or len(self.source_loop.changed_row_binding_ids) != 6
            or len(self.source_loop.preserved_row_binding_ids) != 12
            or model_document.get("occurrence_or_arm_fields_present") is not False
            or model_document.get("private_law_access") is not False
            or proof_document.get("occurrence_field_present") is not False
            or proof_document.get("source_provenance_field_present") is not False
            or proof_document.get("private_law_access") is not False
        ):
            _fail("source recovery overlay is not a promotable query-neutral epoch")
        object.__setattr__(self, "_epoch_id", content_id(EPOCH_DOMAIN, self._payload()))

    @property
    def model(self) -> planning_v2.V075NumericalModelV2:
        return self.source_loop.successor_model

    @property
    def proof(self) -> planning_v2.V075NumericalPlanningProofV2:
        return self.source_loop.successor_proof

    @property
    def source_query(self):
        return self.source_loop.transaction.request.consumption.query

    def _payload(self) -> dict[str, Any]:
        frontier = self.proof.failed_frontier
        assert frontier is not None
        return {
            "schema": "acfqp.construction_k7_recovery_overlay_promoted_epoch.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_recovery_world_model_loop_id": self.source_loop.result_id,
            "source_ground_transaction_id": self.source_loop.transaction.transaction_id,
            "source_recovery_eligible_query_id": self.source_query.query_id,
            "source_logical_occurrence_id": self.source_query.logical_occurrence_id,
            "source_query_ordinal": self.source_query.query_ordinal,
            "promoted_numerical_model_id": self.model.model_id,
            "promoted_numerical_proof_id": self.proof.proof_id,
            "promoted_failed_frontier_id": frontier.frontier_id,
            "promoted_row_count": len(self.model.rows),
            "changed_row_count": len(self.source_loop.changed_row_binding_ids),
            "preserved_row_count": len(self.source_loop.preserved_row_binding_ids),
            "changed_semantic_row_binding_ids": list(
                self.source_loop.changed_row_binding_ids
            ),
            "preserved_semantic_row_binding_ids": list(
                self.source_loop.preserved_row_binding_ids
            ),
            "frontier_row_count": len(frontier.obligations),
            "requestable_frontier_row_count": 0,
            "cap_blocked_frontier_row_count": len(frontier.obligations),
            "source_support_discovery_draw_count": (
                self.source_loop.transaction.support_discovery_draw_count
            ),
            "source_added_validation_draw_count": (
                self.source_loop.added_validation_draw_count
            ),
            "source_total_local_ground_draw_count": (
                self.source_loop.transaction.total_ground_draw_count
            ),
            "promotion_kind": "IMMUTABLE_QUERY_NEUTRAL_RECOVERY_OVERLAY",
            "source_ground_evidence_projected_out_of_model_identity": True,
            "query_identity_outside_model_and_proof": True,
            "automatic_signed_overlay_compilation_present": True,
            "automatic_coordinate_invention_claimed": False,
            "proof_dependency_dag_materialized_for_promoted_epoch": False,
            "complete_proof_bytes_available_for_exact_reuse": True,
            "immutable_promoted_epoch": True,
            "ground_access_during_promotion": 0,
            "planner_call_during_promotion": 0,
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def epoch_id(self) -> str:
        current = content_id(EPOCH_DOMAIN, self._payload())
        if current != self._epoch_id:
            _fail("promoted RAPM epoch changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "recovery_overlay_promoted_epoch_id": self.epoch_id,
        }


def promote_recovery_overlay_epoch_v1(
    source_loop: loop_v1.RecoveryEligibleWorldModelLoopV1,
) -> RecoveryOverlayPromotedEpochV1:
    return RecoveryOverlayPromotedEpochV1(_EPOCH_ISSUER, source_loop)


def require_recovery_overlay_promoted_epoch_v1(
    epoch: RecoveryOverlayPromotedEpochV1,
) -> RecoveryOverlayPromotedEpochV1:
    if type(epoch) is not RecoveryOverlayPromotedEpochV1:
        _fail("promoted RAPM epoch has a foreign type")
    # The expensive source-model structural audit runs once at promotion.
    # Later operational consumers recheck the content-addressed epoch payload
    # without serializing the large exact-rational model again.
    epoch.epoch_id
    return epoch


@dataclass(frozen=True, slots=True)
class RecoveryOverlayPromotedQueryV1:
    _issuer: InitVar[object]
    promoted_epoch_id: str
    promoted_model_id: str
    source_logical_occurrence_id: str
    logical_occurrence_id: str
    query_ordinal: int
    threshold_profile_id: str
    _query_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _QUERY_ISSUER:
            _fail("promoted RAPM query is caller-minted")
        for value, label in (
            (self.promoted_epoch_id, "promoted RAPM epoch"),
            (self.promoted_model_id, "promoted numerical model"),
            (self.source_logical_occurrence_id, "source logical occurrence"),
            (self.logical_occurrence_id, "fresh logical occurrence"),
            (self.threshold_profile_id, "threshold profile"),
        ):
            _cid(value, label)
        if (
            self.logical_occurrence_id == self.source_logical_occurrence_id
            or type(self.query_ordinal) is not int
            or self.query_ordinal <= 2
            or self.threshold_profile_id
            != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        ):
            _fail("promoted RAPM query identity or threshold changed")
        object.__setattr__(self, "_query_id", content_id(QUERY_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_recovery_overlay_promoted_query.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_overlay_promoted_epoch_id": self.promoted_epoch_id,
            "promoted_numerical_model_id": self.promoted_model_id,
            "source_logical_occurrence_id": self.source_logical_occurrence_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "query_ordinal": self.query_ordinal,
            "threshold_profile_id": self.threshold_profile_id,
            "route": "ADAPTIVE_QUOTIENT",
            "promoted_epoch_selected_before_ground_access": True,
            "ground_input_present": False,
        }

    @property
    def query_id(self) -> str:
        current = content_id(QUERY_DOMAIN, self._payload())
        if current != self._query_id:
            _fail("promoted RAPM query changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "recovery_overlay_promoted_query_id": self.query_id}


def freeze_recovery_overlay_promoted_query_v1(
    epoch: RecoveryOverlayPromotedEpochV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> RecoveryOverlayPromotedQueryV1:
    epoch = require_recovery_overlay_promoted_epoch_v1(epoch)
    if query_ordinal != epoch.source_query.query_ordinal + 1:
        _fail("promoted RAPM query is not the next registered occurrence")
    return RecoveryOverlayPromotedQueryV1(
        _QUERY_ISSUER,
        epoch.epoch_id,
        epoch.model.model_id,
        epoch.source_query.logical_occurrence_id,
        _cid(logical_occurrence_id, "fresh logical occurrence"),
        query_ordinal,
        worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id,
    )


@dataclass(frozen=True, slots=True)
class RecoveryOverlayPromotedConsumptionV1:
    _issuer: InitVar[object]
    epoch: RecoveryOverlayPromotedEpochV1 = field(repr=False)
    query: RecoveryOverlayPromotedQueryV1
    _consumption_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _CONSUMPTION_ISSUER
            or type(self.epoch) is not RecoveryOverlayPromotedEpochV1
            or type(self.query) is not RecoveryOverlayPromotedQueryV1
        ):
            _fail("promoted RAPM consumption is caller-minted")
        require_recovery_overlay_promoted_epoch_v1(self.epoch)
        self.query.__post_init__(_QUERY_ISSUER)
        frontier = self.epoch.proof.failed_frontier
        if (
            self.query.promoted_epoch_id != self.epoch.epoch_id
            or self.query.promoted_model_id != self.epoch.model.model_id
            or self.query.source_logical_occurrence_id
            != self.epoch.source_query.logical_occurrence_id
            or frontier is None
            or len(frontier.obligations) != 7
            or any(
                item.next_registered_checkpoint is not None
                for item in frontier.obligations
            )
        ):
            _fail("promoted RAPM consumption crossed its epoch")
        object.__setattr__(
            self,
            "_consumption_id",
            content_id(CONSUMPTION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        frontier = self.epoch.proof.failed_frontier
        assert frontier is not None
        return {
            "schema": "acfqp.construction_k7_recovery_overlay_promoted_consumption.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_overlay_promoted_epoch_id": self.epoch.epoch_id,
            "recovery_overlay_promoted_query_id": self.query.query_id,
            "logical_occurrence_id": self.query.logical_occurrence_id,
            "promoted_numerical_model_id": self.epoch.model.model_id,
            "cached_numerical_proof_id": self.epoch.proof.proof_id,
            "cached_failed_frontier_id": frontier.frontier_id,
            "cached_frontier_row_count": len(frontier.obligations),
            "requestable_frontier_row_count": 0,
            "cap_blocked_frontier_row_count": len(frontier.obligations),
            "complete_proof_bytes_reused": True,
            "proof_dependency_dag_present": False,
            "proof_node_reuse_count": None,
            "proof_node_compute_count": 0,
            "full_planner_call_count": 0,
            "model_construction_repeated": False,
            "new_local_support_discovery_draw_count": 0,
            "new_local_validation_draw_count": 0,
            "new_local_ground_draw_count": 0,
            "ground_input_parameter_present": False,
            "exact_cached_certificate_failure_replayed": True,
            "query_local_ground_recovery_eligible": False,
            "query_local_ground_recovery_executed_here": False,
            "local_allowed_after_result": False,
            "local_forbidden_reason": "ALL_PROMOTED_FRONTIER_ROWS_CAP_BLOCKED",
            "next_required_action": "EXECUTE_QUERY_IDENTITY_BOUND_DIRECT_GROUND_FALLBACK",
            "plan_certificate_issued": False,
            "official_execution_allowed": False,
        }

    @property
    def consumption_id(self) -> str:
        current = content_id(CONSUMPTION_DOMAIN, self._payload())
        if current != self._consumption_id:
            _fail("promoted RAPM consumption changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query": self.query.to_document(),
            "recovery_overlay_promoted_consumption_id": self.consumption_id,
        }


def consume_recovery_overlay_promoted_epoch_v1(
    epoch: RecoveryOverlayPromotedEpochV1,
    query: RecoveryOverlayPromotedQueryV1,
) -> RecoveryOverlayPromotedConsumptionV1:
    return RecoveryOverlayPromotedConsumptionV1(
        _CONSUMPTION_ISSUER,
        require_recovery_overlay_promoted_epoch_v1(epoch),
        query,
    )


@dataclass(frozen=True, slots=True)
class RecoveryOverlayPromotionResultV1:
    _issuer: InitVar[object]
    epoch: RecoveryOverlayPromotedEpochV1 = field(repr=False)
    consumption: RecoveryOverlayPromotedConsumptionV1 = field(repr=False)
    _result_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _RESULT_ISSUER
            or type(self.epoch) is not RecoveryOverlayPromotedEpochV1
            or type(self.consumption) is not RecoveryOverlayPromotedConsumptionV1
        ):
            _fail("recovery-overlay promotion result is caller-minted")
        require_recovery_overlay_promoted_epoch_v1(self.epoch)
        self.consumption.__post_init__(_CONSUMPTION_ISSUER)
        if (
            self.consumption.epoch.epoch_id != self.epoch.epoch_id
            or self.source_local_ground_draw_count != 12_672
            or self.promoted_query_new_local_ground_draw_count != 0
        ):
            _fail("recovery-overlay promotion result crossed its reuse chain")
        object.__setattr__(self, "_result_id", content_id(RESULT_DOMAIN, self._payload()))

    @property
    def source_local_ground_draw_count(self) -> int:
        return self.epoch.source_loop.transaction.total_ground_draw_count

    @property
    def promoted_query_new_local_ground_draw_count(self) -> int:
        return 0

    def _payload(self) -> dict[str, Any]:
        source_draws = self.source_local_ground_draw_count
        return {
            "schema": "acfqp.construction_k7_recovery_overlay_promotion_result.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "recovery_overlay_promoted_epoch_id": self.epoch.epoch_id,
            "recovery_overlay_promoted_consumption_id": (
                self.consumption.consumption_id
            ),
            "source_logical_occurrence_id": (
                self.epoch.source_query.logical_occurrence_id
            ),
            "promoted_query_logical_occurrence_id": (
                self.consumption.query.logical_occurrence_id
            ),
            "source_local_ground_draw_count": source_draws,
            "promoted_query_new_local_ground_draw_count": 0,
            "two_occurrence_promoted_local_ground_draw_count": source_draws,
            "counterfactual_repeated_recovery_local_ground_draw_count": (
                2 * source_draws
            ),
            "local_ground_draws_avoided_under_identical_recovery_recipe": (
                source_draws
            ),
            "local_ground_draw_reduction_fraction": {
                "numerator": 1,
                "denominator": 2,
            },
            "matched_no_promotion_execution_performed": False,
            "reduction_is_exact_recipe_counterfactual_not_official_economics": True,
            "promoted_model_consumed_before_any_new_ground_access": True,
            "cached_failure_routed_without_repeating_local_recovery": True,
            "downstream_direct_fallback_executed_here": False,
            "end_to_end_sample_efficiency_claimed": False,
            "abstract_plan_certificate_issued": False,
            "automatic_coordinate_invention_claimed": False,
            "official_scalar_cost": None,
            "official_N_break_even": None,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
            "next_required_action": "EXECUTE_FRESH_QUERY_DIRECT_FALLBACK_OR_FIND_CERTIFYING_OVERLAY",
        }

    @property
    def result_id(self) -> str:
        current = content_id(RESULT_DOMAIN, self._payload())
        if current != self._result_id:
            _fail("recovery-overlay promotion result changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "promoted_epoch": self.epoch.to_document(),
            "promoted_consumption": self.consumption.to_document(),
            "recovery_overlay_promotion_result_id": self.result_id,
        }


def run_recovery_overlay_promotion_v1(
    source_loop: loop_v1.RecoveryEligibleWorldModelLoopV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> RecoveryOverlayPromotionResultV1:
    epoch = promote_recovery_overlay_epoch_v1(source_loop)
    query = freeze_recovery_overlay_promoted_query_v1(
        epoch,
        logical_occurrence_id=logical_occurrence_id,
        query_ordinal=query_ordinal,
    )
    consumption = consume_recovery_overlay_promoted_epoch_v1(epoch, query)
    return RecoveryOverlayPromotionResultV1(
        _RESULT_ISSUER,
        epoch,
        consumption,
    )


def verify_recovery_overlay_promotion_v1(
    claimed: RecoveryOverlayPromotionResultV1,
) -> RecoveryOverlayPromotionResultV1:
    if type(claimed) is not RecoveryOverlayPromotionResultV1:
        _fail("recovery-overlay promotion result has a foreign type")
    expected = run_recovery_overlay_promotion_v1(
        claimed.epoch.source_loop,
        logical_occurrence_id=claimed.consumption.query.logical_occurrence_id,
        query_ordinal=claimed.consumption.query.query_ordinal,
    )
    if canonical_json_bytes(expected.to_document()) != canonical_json_bytes(
        claimed.to_document()
    ):
        _fail("recovery-overlay promotion differs from exact replay")
    return expected


def verify_recovery_overlay_promotion_bytes_v1(
    *,
    source_loop: loop_v1.RecoveryEligibleWorldModelLoopV1,
    result_bytes: bytes,
) -> RecoveryOverlayPromotionResultV1:
    if type(result_bytes) is not bytes:
        _fail("recovery-overlay promotion result must be canonical bytes")
    try:
        document = loads_canonical_json(result_bytes)
        consumption = document["promoted_consumption"]
        query = consumption["query"]
        expected = run_recovery_overlay_promotion_v1(
            source_loop,
            logical_occurrence_id=query["logical_occurrence_id"],
            query_ordinal=query["query_ordinal"],
        )
    except ConstructionK7RecoveryOverlayPromotionV1Error:
        raise
    except Exception as error:
        raise ConstructionK7RecoveryOverlayPromotionV1Error(
            "recovery-overlay promotion bytes failed typed replay"
        ) from error
    if canonical_json_bytes(document) != result_bytes or canonical_json_bytes(
        expected.to_document()
    ) != result_bytes:
        _fail("recovery-overlay promotion bytes differ from exact replay")
    return expected


__all__ = [
    "ConstructionK7RecoveryOverlayPromotionV1Error",
    "LOCAL_DOMAINS",
    "RecoveryOverlayPromotedConsumptionV1",
    "RecoveryOverlayPromotedEpochV1",
    "RecoveryOverlayPromotedQueryV1",
    "RecoveryOverlayPromotionResultV1",
    "consume_recovery_overlay_promoted_epoch_v1",
    "freeze_recovery_overlay_promoted_query_v1",
    "promote_recovery_overlay_epoch_v1",
    "require_recovery_overlay_promoted_epoch_v1",
    "run_recovery_overlay_promotion_v1",
    "verify_recovery_overlay_promotion_bytes_v1",
    "verify_recovery_overlay_promotion_v1",
]
