"""Producer-free bytes replay for cross-occurrence recovery-overlay reuse.

The verifier accepts the exact predecessor checkpoint, closed local-ground
transaction, world-model loop, and lightweight promotion result.  It delegates
only the predecessor numerical reconstruction to the already independent H=2
loop verifier, then reconstructs the promoted epoch/query/consumption/result
documents locally from those verified bytes.  It imports neither promotion nor
recovery-loop producer code.
"""

from __future__ import annotations

from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import hashlib
from typing import Any, NoReturn

from acfqp import construction_k7_recovery_eligible_world_model_loop_independent_verifier_v1 as loop_verifier_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.114"
PROFILE_KEY = (
    "construction_k7_recovery_overlay_promotion_independent_verifier_v1"
)

EPOCH_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_EPOCH_V1_DOMAIN
QUERY_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_QUERY_V1_DOMAIN
CONSUMPTION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTED_CONSUMPTION_V1_DOMAIN
)
RESULT_DOMAIN = CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_RESULT_V1_DOMAIN
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_OVERLAY_PROMOTION_INDEPENDENT_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if len(LOCAL_DOMAINS) != 1 or not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("promotion independent-verification domain is not central")


class ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
    ValueError
):
    """The predecessor bytes or promotion identity graph changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _load(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty canonical bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


@dataclass(frozen=True, slots=True)
class _VerifiedSourceV1:
    checkpoint_id: str
    ground_transaction_id: str
    world_model_loop_id: str
    source_query_id: str
    source_logical_occurrence_id: str
    source_query_ordinal: int
    threshold_profile_id: str
    promoted_model_id: str
    promoted_proof_id: str
    promoted_frontier_id: str
    promoted_row_count: int
    changed_binding_ids: tuple[str, ...]
    preserved_binding_ids: tuple[str, ...]
    frontier_row_count: int
    source_support_discovery_draw_count: int
    source_added_validation_draw_count: int
    source_total_local_ground_draw_count: int
    predecessor_verification_id: str
    checkpoint_sha256: str
    transaction_sha256: str
    loop_sha256: str


@lru_cache(maxsize=4)
def _verify_source_bytes(
    checkpoint_bytes: bytes,
    ground_transaction_bytes: bytes,
    world_model_loop_bytes: bytes,
) -> _VerifiedSourceV1:
    try:
        verification = (
            loop_verifier_v1.verify_recovery_eligible_world_model_loop_bytes_v1(
                checkpoint_bytes=checkpoint_bytes,
                ground_transaction_bytes=ground_transaction_bytes,
                world_model_loop_bytes=world_model_loop_bytes,
            )
        )
    except Exception as error:
        raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
            "promotion predecessor failed independent H=2 replay"
        ) from error
    checkpoint = _load(checkpoint_bytes, "promotion predecessor checkpoint")
    transaction = _load(
        ground_transaction_bytes, "promotion predecessor ground transaction"
    )
    result = _load(world_model_loop_bytes, "promotion predecessor world-model loop")
    try:
        request = transaction["request"]
        native_occurrence = transaction["native_occurrence"]
        model = result["successor_model"]
        proof = result["successor_proof"]
        frontier = proof["failed_frontier"]
        obligations = frontier["obligations"]
        changed = tuple(result["changed_semantic_row_binding_ids"])
        preserved = tuple(result["preserved_semantic_row_binding_ids"])
        facts = _VerifiedSourceV1(
            _cid(
                checkpoint["recovery_eligible_checkpoint_id"],
                "predecessor checkpoint",
            ),
            _cid(
                transaction["recovery_eligible_ground_transaction_id"],
                "predecessor ground transaction",
            ),
            _cid(
                result["recovery_eligible_world_model_loop_id"],
                "predecessor world-model loop",
            ),
            _cid(request["recovery_eligible_query_id"], "predecessor query"),
            _cid(request["logical_occurrence_id"], "predecessor occurrence"),
            2,
            _cid(native_occurrence["threshold_profile_id"], "threshold profile"),
            _cid(model["model_id"], "promoted model"),
            _cid(proof["proof_id"], "promoted proof"),
            _cid(frontier["frontier_id"], "promoted failed frontier"),
            len(model["rows"]),
            changed,
            preserved,
            len(obligations),
            result["support_discovery_draw_count"],
            result["added_signed_validation_draw_count"],
            result["total_local_ground_draw_count"],
            _cid(verification["verification_id"], "predecessor verification"),
            hashlib.sha256(checkpoint_bytes).hexdigest(),
            hashlib.sha256(ground_transaction_bytes).hexdigest(),
            hashlib.sha256(world_model_loop_bytes).hexdigest(),
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
            "promotion predecessor summary failed typed extraction"
        ) from error
    if (
        verification.get("valid") is not True
        or verification.get("world_model_loop_id") != facts.world_model_loop_id
        or verification.get("ground_transaction_id") != facts.ground_transaction_id
        or verification.get("recovery_eligible_checkpoint_id")
        != facts.checkpoint_id
        or verification.get("successor_numerical_model_id")
        != facts.promoted_model_id
        or verification.get("successor_numerical_proof_id")
        != facts.promoted_proof_id
        or facts.source_query_ordinal != 2
        or facts.promoted_row_count != 18
        or len(facts.changed_binding_ids) != 6
        or len(facts.preserved_binding_ids) != 12
        or facts.frontier_row_count != 7
        or any(item["next_registered_checkpoint"] is not None for item in obligations)
        or facts.source_support_discovery_draw_count != 384
        or facts.source_added_validation_draw_count != 12_288
        or facts.source_total_local_ground_draw_count != 12_672
        or model.get("occurrence_or_arm_fields_present") is not False
        or model.get("private_law_access") is not False
        or proof.get("occurrence_field_present") is not False
        or proof.get("source_provenance_field_present") is not False
        or proof.get("private_law_access") is not False
        or result.get("proof_still_failed") is not True
    ):
        _fail("promotion predecessor is not the exact exhausted recovery overlay")
    return facts


def _expected_promotion_document(
    source: _VerifiedSourceV1,
    *,
    logical_occurrence_id: str,
    query_ordinal: int,
) -> tuple[dict[str, Any], str, str, str, str]:
    logical_occurrence_id = _cid(
        logical_occurrence_id, "promoted-query logical occurrence"
    )
    if (
        logical_occurrence_id == source.source_logical_occurrence_id
        or type(query_ordinal) is not int
        or query_ordinal != source.source_query_ordinal + 1
    ):
        _fail("promoted query is not the next fresh occurrence")
    epoch_payload = {
        "schema": "acfqp.construction_k7_recovery_overlay_promoted_epoch.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.113",
        "profile_key": "construction_k7_recovery_overlay_promotion_v1",
        "source_recovery_world_model_loop_id": source.world_model_loop_id,
        "source_ground_transaction_id": source.ground_transaction_id,
        "source_recovery_eligible_query_id": source.source_query_id,
        "source_logical_occurrence_id": source.source_logical_occurrence_id,
        "source_query_ordinal": source.source_query_ordinal,
        "promoted_numerical_model_id": source.promoted_model_id,
        "promoted_numerical_proof_id": source.promoted_proof_id,
        "promoted_failed_frontier_id": source.promoted_frontier_id,
        "promoted_row_count": source.promoted_row_count,
        "changed_row_count": len(source.changed_binding_ids),
        "preserved_row_count": len(source.preserved_binding_ids),
        "changed_semantic_row_binding_ids": list(source.changed_binding_ids),
        "preserved_semantic_row_binding_ids": list(source.preserved_binding_ids),
        "frontier_row_count": source.frontier_row_count,
        "requestable_frontier_row_count": 0,
        "cap_blocked_frontier_row_count": source.frontier_row_count,
        "source_support_discovery_draw_count": (
            source.source_support_discovery_draw_count
        ),
        "source_added_validation_draw_count": (
            source.source_added_validation_draw_count
        ),
        "source_total_local_ground_draw_count": (
            source.source_total_local_ground_draw_count
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
    epoch_id = content_id(EPOCH_DOMAIN, epoch_payload)
    epoch = {
        **epoch_payload,
        "recovery_overlay_promoted_epoch_id": epoch_id,
    }
    query_payload = {
        "schema": "acfqp.construction_k7_recovery_overlay_promoted_query.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.113",
        "profile_key": "construction_k7_recovery_overlay_promotion_v1",
        "recovery_overlay_promoted_epoch_id": epoch_id,
        "promoted_numerical_model_id": source.promoted_model_id,
        "source_logical_occurrence_id": source.source_logical_occurrence_id,
        "logical_occurrence_id": logical_occurrence_id,
        "query_ordinal": query_ordinal,
        "threshold_profile_id": source.threshold_profile_id,
        "route": "ADAPTIVE_QUOTIENT",
        "promoted_epoch_selected_before_ground_access": True,
        "ground_input_present": False,
    }
    query_id = content_id(QUERY_DOMAIN, query_payload)
    query = {**query_payload, "recovery_overlay_promoted_query_id": query_id}
    consumption_payload = {
        "schema": "acfqp.construction_k7_recovery_overlay_promoted_consumption.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.113",
        "profile_key": "construction_k7_recovery_overlay_promotion_v1",
        "recovery_overlay_promoted_epoch_id": epoch_id,
        "recovery_overlay_promoted_query_id": query_id,
        "logical_occurrence_id": logical_occurrence_id,
        "promoted_numerical_model_id": source.promoted_model_id,
        "cached_numerical_proof_id": source.promoted_proof_id,
        "cached_failed_frontier_id": source.promoted_frontier_id,
        "cached_frontier_row_count": source.frontier_row_count,
        "requestable_frontier_row_count": 0,
        "cap_blocked_frontier_row_count": source.frontier_row_count,
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
    consumption_id = content_id(CONSUMPTION_DOMAIN, consumption_payload)
    consumption = {
        **consumption_payload,
        "query": query,
        "recovery_overlay_promoted_consumption_id": consumption_id,
    }
    source_draws = source.source_total_local_ground_draw_count
    result_payload = {
        "schema": "acfqp.construction_k7_recovery_overlay_promotion_result.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.113",
        "profile_key": "construction_k7_recovery_overlay_promotion_v1",
        "recovery_overlay_promoted_epoch_id": epoch_id,
        "recovery_overlay_promoted_consumption_id": consumption_id,
        "source_logical_occurrence_id": source.source_logical_occurrence_id,
        "promoted_query_logical_occurrence_id": logical_occurrence_id,
        "source_local_ground_draw_count": source_draws,
        "promoted_query_new_local_ground_draw_count": 0,
        "two_occurrence_promoted_local_ground_draw_count": source_draws,
        "counterfactual_repeated_recovery_local_ground_draw_count": 2 * source_draws,
        "local_ground_draws_avoided_under_identical_recovery_recipe": source_draws,
        "local_ground_draw_reduction_fraction": Fraction(1, 2),
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
    result_id = content_id(RESULT_DOMAIN, result_payload)
    result = {
        **result_payload,
        "promoted_epoch": epoch,
        "promoted_consumption": consumption,
        "recovery_overlay_promotion_result_id": result_id,
    }
    return result, epoch_id, query_id, consumption_id, result_id


def verify_recovery_overlay_promotion_bytes_v1(
    *,
    checkpoint_bytes: bytes,
    ground_transaction_bytes: bytes,
    world_model_loop_bytes: bytes,
    promotion_result_bytes: bytes,
) -> dict[str, Any]:
    """Independently reconstruct one promoted cross-occurrence reuse chain."""

    source = _verify_source_bytes(
        checkpoint_bytes,
        ground_transaction_bytes,
        world_model_loop_bytes,
    )
    claimed = _load(promotion_result_bytes, "promotion result")
    try:
        query = claimed["promoted_consumption"]["query"]
        expected, epoch_id, query_id, consumption_id, result_id = (
            _expected_promotion_document(
                source,
                logical_occurrence_id=query["logical_occurrence_id"],
                query_ordinal=query["query_ordinal"],
            )
        )
    except ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error(
            "promotion result failed typed identity extraction"
        ) from error
    if canonical_json_bytes(expected) != promotion_result_bytes:
        _fail("promotion result differs from independent reconstruction")
    payload = {
        "schema": "acfqp.construction_k7_recovery_overlay_promotion_independent_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "recovery_eligible_checkpoint_id": source.checkpoint_id,
        "ground_transaction_id": source.ground_transaction_id,
        "world_model_loop_id": source.world_model_loop_id,
        "predecessor_independent_verification_id": (
            source.predecessor_verification_id
        ),
        "recovery_overlay_promoted_epoch_id": epoch_id,
        "recovery_overlay_promoted_query_id": query_id,
        "recovery_overlay_promoted_consumption_id": consumption_id,
        "recovery_overlay_promotion_result_id": result_id,
        "checkpoint_sha256": source.checkpoint_sha256,
        "ground_transaction_sha256": source.transaction_sha256,
        "world_model_loop_sha256": source.loop_sha256,
        "promotion_result_sha256": hashlib.sha256(promotion_result_bytes).hexdigest(),
        "source_h2_proof_independently_recomputed": True,
        "successor_h2_proof_independently_recomputed": True,
        "promoted_epoch_identity_independently_recomputed": True,
        "fresh_query_identity_independently_recomputed": True,
        "cached_failure_consumption_independently_recomputed": True,
        "new_local_ground_draw_count_verified": 0,
        "local_recovery_reopened": False,
        "verified_next_route": "QUERY_IDENTITY_BOUND_DIRECT_GROUND_FALLBACK",
        "promotion_producer_imported": False,
        "recovery_loop_producer_imported": False,
        "verification_lane": "EVALUATION",
        "verification_work_included_in_operational_route_work": False,
        "abstract_plan_certificate_verified": False,
        "official_execution_allowed": False,
        "valid": True,
    }
    return {
        **payload,
        "verification_id": content_id(VERIFICATION_DOMAIN, payload),
    }


__all__ = [
    "ConstructionK7RecoveryOverlayPromotionIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "verify_recovery_overlay_promotion_bytes_v1",
]
