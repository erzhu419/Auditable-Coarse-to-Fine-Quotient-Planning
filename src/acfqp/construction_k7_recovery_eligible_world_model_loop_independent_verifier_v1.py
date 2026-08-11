"""Independent bytes verifier for one recovery-eligible H=2 loop.

This module deliberately does not import either recovery-eligible producer.
It accepts only three canonical documents: the as-of checkpoint, the closed
ground transaction, and the immutable-overlay result.  It reconstructs both
numerical models, independently replans both H=2 proofs, checks every embedded
validation batch and delta content ID, and independently projects the six
signed aggregate-count deltas onto the source model's frozen support.

The closed observer document is only a compact in-process closure summary: it
does not carry discovery batches or the observer public key.  Consequently
this verifier does not claim portable discovery-batch replay or independent
RSA signature verification.  Those missing claims remain explicit.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
from typing import Any, Mapping, NoReturn

from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.112"
PROFILE_KEY = "construction_k7_recovery_eligible_world_model_loop_independent_verifier_v1"
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_VERIFICATION_V1_DOMAIN
)

_OCCURRENCE_DOMAIN = "acfqp:v075-batch-native-occurrence:v1"
_BATCH_REQUEST_DOMAIN = "acfqp:v075-batch-observation-request:v2"
_BATCH_OUTCOME_DOMAIN = "acfqp:v075-batch-outcome-aggregate:v2"
_BATCH_DOMAIN = "acfqp:v075-signed-observation-batch:v2"
_DELTA_DOMAIN = "acfqp:v075-query-bound-validation-delta:v2"


class ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
    ValueError
):
    """The portable checkpoint, transaction, overlay, or proof changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _load(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes:
        _fail(f"{label} bytes are absent")
    try:
        value = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


def _exact(document: Mapping[str, Any], fields: set[str], label: str) -> None:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} fields changed")


def _raw_id(domain: str, payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(dict(payload))
    ).hexdigest()


def _fraction(document: Any, label: str) -> Fraction:
    if type(document) is Fraction:
        return document
    if (
        type(document) is not dict
        or set(document) != {"numerator", "denominator"}
        or type(document.get("numerator")) is not int
        or type(document.get("denominator")) is not int
        or document["denominator"] <= 0
    ):
        _fail(f"{label} is not one reduced rational document")
    value = Fraction(document["numerator"], document["denominator"])
    if value.numerator != document["numerator"] or value.denominator != document["denominator"]:
        _fail(f"{label} is not reduced")
    return value


_CHECKPOINT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_persistent_proof_cache_id",
    "source_bundle_binding_id",
    "source_logical_occurrence_id",
    "source_final_local_replanning_id",
    "source_proof_dependency_graph_id",
    "published_numerical_model_id",
    "published_numerical_proof_id",
    "published_failed_frontier_id",
    "proof_node_ids",
    "proof_node_count",
    "frontier_row_count",
    "requestable_frontier_row_count",
    "cap_blocked_frontier_row_count",
    "requested_additional_draw_count",
    "publication_cut",
    "immutable_as_of_checkpoint",
    "later_target_graph_input_present_in_online_api",
    "deliberately_coarsened_partition_used",
    "production_latest_epoch_selection_authority",
    "construction_fixture",
    "portable_checkpoint_loader_present",
    "ground_access_count",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "source_graph",
    "recovery_eligible_checkpoint_id",
}


def _verify_checkpoint(
    document: dict[str, Any],
) -> tuple[str, planning_v2.V075NumericalModelV2, planning_v2.V075NumericalPlanningProofV2]:
    _exact(document, _CHECKPOINT_FIELDS, "recovery-eligible checkpoint")
    graph = document["source_graph"]
    if type(graph) is not dict:
        _fail("recovery-eligible checkpoint lacks its source graph")
    try:
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(graph["numerical_model"])
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(graph["numerical_proof"])
        )
    except (KeyError, TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
            "checkpoint source numerical graph is invalid"
        ) from error
    recomputed = planning_v2.plan_v075_construction_numerical_model_v2(
        model=model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    frontier = proof.failed_frontier
    if (
        proof.model != model
        or canonical_json_bytes(recomputed.to_document())
        != canonical_json_bytes(proof.to_document())
        or frontier is None
        or graph.get("proof_dependency_graph_id")
        != document["source_proof_dependency_graph_id"]
        or model.model_id != document["published_numerical_model_id"]
        or proof.proof_id != document["published_numerical_proof_id"]
        or frontier.frontier_id != document["published_failed_frontier_id"]
        or len(model.rows) != 18
        or len(frontier.obligations) != 7
        or sum(item.next_registered_checkpoint is not None for item in frontier.obligations)
        != 6
        or sum(
            0
            if item.next_registered_checkpoint is None
            else item.next_registered_checkpoint - item.current_validation_draw_count
            for item in frontier.obligations
        )
        != 12_288
        or document["proof_node_count"] != 41
        or type(document["proof_node_ids"]) is not list
        or len(document["proof_node_ids"]) != 41
        or len(set(document["proof_node_ids"])) != 41
        or document["frontier_row_count"] != 7
        or document["requestable_frontier_row_count"] != 6
        or document["cap_blocked_frontier_row_count"] != 1
        or document["requested_additional_draw_count"] != 12_288
        or document["publication_cut"]
        != "TRANSACTION_1_REPLANNING_AS_OF_CHECKPOINT"
        or document["immutable_as_of_checkpoint"] is not True
        or document["later_target_graph_input_present_in_online_api"] is not False
        or document["deliberately_coarsened_partition_used"] is not False
        or document["production_latest_epoch_selection_authority"] is not False
        or document["construction_fixture"] is not True
        or document["portable_checkpoint_loader_present"] is not False
        or document["ground_access_count"] != 0
        or document["plan_certificate_issued"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("recovery-eligible checkpoint semantics changed")
    payload = dict(document)
    supplied = payload.pop("recovery_eligible_checkpoint_id")
    payload.pop("source_graph")
    if supplied != content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CHECKPOINT_FIXTURE_V1_DOMAIN,
        payload,
    ):
        _fail("recovery-eligible checkpoint content ID changed")
    return supplied, model, proof


_ROW_REQUEST_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "numerical_row_id",
    "semantic_row_binding_id",
    "current_validation_draw_count",
    "next_registered_checkpoint",
    "requested_additional_draw_count",
    "disposition",
    "selected_from_cached_failed_frontier",
    "ground_access_performed",
    "validation_request_id",
}


def _verify_request(
    document: dict[str, Any],
    *,
    checkpoint_id: str,
    model: planning_v2.V075NumericalModelV2,
    proof: planning_v2.V075NumericalPlanningProofV2,
    source_logical_occurrence_id: str,
) -> tuple[str, str, tuple[dict[str, Any], ...]]:
    fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "recovery_eligible_checkpoint_id",
        "recovery_eligible_checkpoint_consumption_id",
        "recovery_eligible_query_id",
        "logical_occurrence_id",
        "source_numerical_model_id",
        "source_numerical_proof_id",
        "source_frontier_id",
        "transaction_index",
        "maximum_local_transactions_per_logical_occurrence",
        "validation_request_ids",
        "requested_row_count",
        "cap_blocked_row_count",
        "requested_additional_draw_count",
        "selection_rule",
        "activation_state",
        "request_frozen_after_exact_cached_certificate_failure",
        "request_frozen_before_namespace_creation",
        "observer_input_present",
        "signer_input_present",
        "kernel_input_present",
        "private_law_input_present",
        "ground_tape_input_present",
        "ground_access_count",
        "ground_execution_authorized_here",
        "next_required_action",
        "plan_certificate_issued",
        "official_execution_allowed",
        "validation_requests",
        "recovery_eligible_recovery_request_id",
    }
    _exact(document, fields, "recovery-eligible recovery request")
    rows = document["validation_requests"]
    frontier = proof.failed_frontier
    assert frontier is not None
    model_by_id = {item.row_id: item for item in model.rows}
    frontier_by_id = {item.row_id: item for item in frontier.obligations}
    if type(rows) is not list or len(rows) != 7:
        _fail("recovery request row inventory changed")
    verified = []
    requested = []
    blocked = []
    for row in rows:
        _exact(row, _ROW_REQUEST_FIELDS, "recovery validation request")
        payload = dict(row)
        supplied = payload.pop("validation_request_id")
        if supplied != content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_VALIDATION_REQUEST_V1_DOMAIN,
            payload,
        ):
            _fail("recovery validation request content ID changed")
        model_row = model_by_id.get(row["numerical_row_id"])
        obligation = frontier_by_id.get(row["numerical_row_id"])
        if (
            model_row is None
            or obligation is None
            or model_row.row_binding_id != row["semantic_row_binding_id"]
            or obligation.current_validation_draw_count
            != row["current_validation_draw_count"]
            or obligation.next_registered_checkpoint
            != row["next_registered_checkpoint"]
            or row["selected_from_cached_failed_frontier"] is not True
            or row["ground_access_performed"] is not False
        ):
            _fail("recovery validation request crossed the cached frontier")
        if row["disposition"] == "REQUEST_NEXT_REGISTERED_CHECKPOINT":
            if (
                row["next_registered_checkpoint"] is None
                or row["requested_additional_draw_count"] != 2_048
            ):
                _fail("recovery validation checkpoint delta changed")
            requested.append(row)
        elif row["disposition"] == "CAP_BLOCKED_NO_REGISTERED_CHECKPOINT":
            if (
                row["next_registered_checkpoint"] is not None
                or row["requested_additional_draw_count"] != 0
            ):
                _fail("cap-blocked recovery row changed")
            blocked.append(row)
        else:
            _fail("recovery validation disposition changed")
        verified.append(row)
    if (
        [row["numerical_row_id"] for row in verified]
        != sorted({row["numerical_row_id"] for row in verified})
        or len(requested) != 6
        or len(blocked) != 1
        or document["validation_request_ids"]
        != [row["validation_request_id"] for row in verified]
        or document["requested_row_count"] != 6
        or document["cap_blocked_row_count"] != 1
        or document["requested_additional_draw_count"] != 12_288
        or document["recovery_eligible_checkpoint_id"] != checkpoint_id
        or document["logical_occurrence_id"] == source_logical_occurrence_id
        or document["source_numerical_model_id"] != model.model_id
        or document["source_numerical_proof_id"] != proof.proof_id
        or document["source_frontier_id"] != frontier.frontier_id
        or document["transaction_index"] != 1
        or document["maximum_local_transactions_per_logical_occurrence"] != 2
        or document["selection_rule"]
        != "ALL_AND_ONLY_CACHED_FRONTIER_ROWS_WITH_NEXT_REGISTERED_CHECKPOINT"
        or document["activation_state"] != "PREPARED_NO_ACCESS"
        or any(
            document[key] is not expected
            for key, expected in {
                "request_frozen_after_exact_cached_certificate_failure": True,
                "request_frozen_before_namespace_creation": True,
                "observer_input_present": False,
                "signer_input_present": False,
                "kernel_input_present": False,
                "private_law_input_present": False,
                "ground_tape_input_present": False,
                "ground_execution_authorized_here": False,
                "plan_certificate_issued": False,
                "official_execution_allowed": False,
            }.items()
        )
        or document["ground_access_count"] != 0
    ):
        _fail("recovery request no-access contract changed")
    payload = dict(document)
    supplied = payload.pop("recovery_eligible_recovery_request_id")
    payload.pop("validation_requests")
    if supplied != content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_RECOVERY_REQUEST_V1_DOMAIN,
        payload,
    ):
        _fail("recovery request content ID changed")
    return supplied, document["logical_occurrence_id"], tuple(requested)


def _verify_occurrence(document: dict[str, Any]) -> str:
    fields = {
        "schema",
        "schema_version",
        "target_tape_namespace_id",
        "context_id",
        "arm",
        "occurrence_ordinal",
        "threshold_profile_id",
        "cap_profile_id",
        "source_transport_id",
        "occurrence_id",
        "frozen_before_observation",
        "batch_count_at_freeze",
        "observer_calls",
        "kernel_calls",
        "target_accessed",
        "private_material_serialized",
    }
    _exact(document, fields, "native occurrence")
    identity_fields = {
        "schema",
        "schema_version",
        "target_tape_namespace_id",
        "context_id",
        "arm",
        "occurrence_ordinal",
        "threshold_profile_id",
        "cap_profile_id",
        "source_transport_id",
    }
    if (
        document["occurrence_id"]
        != _raw_id(_OCCURRENCE_DOMAIN, {key: document[key] for key in identity_fields})
        or document["arm"] != "NO_PRIOR"
        or document["occurrence_ordinal"] != 0
        or document["source_transport_id"] is not None
        or document["frozen_before_observation"] is not True
        or document["batch_count_at_freeze"] != 0
        or document["observer_calls"] != 0
        or document["kernel_calls"] != 0
        or document["target_accessed"] is not False
        or document["private_material_serialized"] is not False
    ):
        _fail("native occurrence was not frozen before ground access")
    return document["occurrence_id"]


_ACQUISITION_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "validation_request_id",
    "numerical_row_id",
    "semantic_row_binding_id",
    "discovery_intent_id",
    "discovery_batch_id",
    "discovery_append_receipt_id",
    "support_freeze_id",
    "validation_intent_id",
    "validation_batch_id",
    "validation_append_receipt_id",
    "support_discovery_draw_count",
    "requested_validation_draw_count",
    "support_frozen_before_validation",
    "observer_signed_discovery_and_validation",
    "selected_from_cached_failed_proof_frontier",
    "ground_access_performed",
    "row_acquisition_id",
}


def _verify_transaction(
    document: dict[str, Any],
    *,
    checkpoint_id: str,
    model: planning_v2.V075NumericalModelV2,
    proof: planning_v2.V075NumericalPlanningProofV2,
    source_logical_occurrence_id: str,
) -> tuple[str, tuple[dict[str, Any], ...], str]:
    fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "recovery_eligible_recovery_request_id",
        "logical_occurrence_id",
        "namespace_binding_id",
        "target_tape_namespace_id",
        "native_occurrence_id",
        "observer_control_closure_id",
        "observer_reconciliation_id",
        "row_acquisition_ids",
        "requested_row_count",
        "cap_blocked_row_count",
        "support_discovery_draw_count",
        "requested_validation_draw_count",
        "total_ground_draw_count",
        "request_verified_before_namespace_creation",
        "namespace_bound_before_ground_access",
        "only_requested_rows_executed",
        "cap_blocked_rows_not_accessed",
        "observer_closed_and_exactly_reconciled",
        "fresh_query_ground_recovery_executed",
        "ground_access_after_observer_closure",
        "immutable_overlay_compiled",
        "post_transaction_replanning_performed",
        "next_required_action",
        "construction_only",
        "plan_certificate_issued",
        "campaign_closure_issued",
        "official_execution_allowed",
        "request",
        "namespace_binding",
        "native_occurrence",
        "row_acquisitions",
        "observer_closure",
        "recovery_eligible_ground_transaction_id",
    }
    _exact(document, fields, "recovery-eligible ground transaction")
    request_id, occurrence_id, requested = _verify_request(
        document["request"],
        checkpoint_id=checkpoint_id,
        model=model,
        proof=proof,
        source_logical_occurrence_id=source_logical_occurrence_id,
    )
    native_id = _verify_occurrence(document["native_occurrence"])
    namespace = document["namespace_binding"]
    namespace_fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "recovery_eligible_recovery_request_id",
        "logical_occurrence_id",
        "target_tape_namespace_id",
        "native_occurrence_id",
        "private_environment_generation_id",
        "context_id",
        "arm",
        "request_verified_before_namespace_creation",
        "namespace_ground_access_count_at_binding",
        "construction_only",
        "production_authorizing",
        "official_execution_allowed",
        "namespace_binding_id",
    }
    _exact(namespace, namespace_fields, "recovery namespace binding")
    namespace_payload = dict(namespace)
    namespace_id = namespace_payload.pop("namespace_binding_id")
    if (
        namespace_id
        != content_id(
            CONSTRUCTION_K7_RECOVERY_ELIGIBLE_NAMESPACE_BINDING_V1_DOMAIN,
            namespace_payload,
        )
        or namespace["recovery_eligible_recovery_request_id"] != request_id
        or namespace["logical_occurrence_id"] != occurrence_id
        or namespace["target_tape_namespace_id"]
        != document["native_occurrence"]["target_tape_namespace_id"]
        or namespace["native_occurrence_id"] != native_id
        or namespace["context_id"] != model.context.context_id
        or namespace["arm"] != "NO_PRIOR"
        or namespace["request_verified_before_namespace_creation"] is not True
        or namespace["namespace_ground_access_count_at_binding"] != 0
        or namespace["production_authorizing"] is not False
        or namespace["official_execution_allowed"] is not False
    ):
        _fail("recovery namespace binding changed")
    acquisitions = document["row_acquisitions"]
    if type(acquisitions) is not list or len(acquisitions) != 6:
        _fail("recovery acquisition inventory changed")
    for acquisition, request in zip(acquisitions, requested, strict=True):
        _exact(acquisition, _ACQUISITION_FIELDS, "recovery row acquisition")
        payload = dict(acquisition)
        supplied = payload.pop("row_acquisition_id")
        if (
            supplied
            != content_id(
                CONSTRUCTION_K7_RECOVERY_ELIGIBLE_ROW_ACQUISITION_V1_DOMAIN,
                payload,
            )
            or acquisition["validation_request_id"]
            != request["validation_request_id"]
            or acquisition["numerical_row_id"] != request["numerical_row_id"]
            or acquisition["semantic_row_binding_id"]
            != request["semantic_row_binding_id"]
            or acquisition["support_discovery_draw_count"] != 64
            or acquisition["requested_validation_draw_count"] != 2_048
            or acquisition["support_frozen_before_validation"] is not True
            or acquisition["observer_signed_discovery_and_validation"] is not True
            or acquisition["selected_from_cached_failed_proof_frontier"] is not True
            or acquisition["ground_access_performed"] is not True
        ):
            _fail("recovery row acquisition crossed its request")
    closure = document["observer_closure"]
    closure_fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "batch_journal_closure_id",
        "control_closure_id",
        "reconciliation_id",
        "head_ids",
        "intent_ids",
        "append_receipt_ids",
        "support_freeze_ids",
        "support_freeze_count",
        "official_execution_allowed",
        "production_authorizing",
        "process_isolation_provided",
        "python_wrapper_is_not_process_isolation",
        "trusted_in_process_wrapper_order_replayed",
        "single_private_boundary_atomicity_proven",
        "exclusive_signer_ownership_proven",
        "wrapper_signer_reference_cleared_after_both_closures",
        "terminal_class",
    }
    _exact(closure, closure_fields, "observer closure summary")
    if (
        closure["support_freeze_count"] != 6
        or closure["support_freeze_ids"]
        != [item["support_freeze_id"] for item in acquisitions]
        or closure["intent_ids"]
        != [value for item in acquisitions for value in (item["discovery_intent_id"], item["validation_intent_id"])]
        or closure["append_receipt_ids"]
        != [value for item in acquisitions for value in (item["discovery_append_receipt_id"], item["validation_append_receipt_id"])]
        or len(closure["head_ids"]) != 13
        or closure["terminal_class"] != "ATTEMPT_CLOSURE_NONCERTIFICATE"
        or closure["trusted_in_process_wrapper_order_replayed"] is not True
        or closure["wrapper_signer_reference_cleared_after_both_closures"] is not True
        or closure["official_execution_allowed"] is not False
        or closure["production_authorizing"] is not False
        or closure["process_isolation_provided"] is not False
        or closure["single_private_boundary_atomicity_proven"] is not False
        or closure["exclusive_signer_ownership_proven"] is not False
    ):
        _fail("observer closure summary or acquisition joins changed")
    if (
        document["recovery_eligible_recovery_request_id"] != request_id
        or document["logical_occurrence_id"] != occurrence_id
        or document["namespace_binding_id"] != namespace_id
        or document["native_occurrence_id"] != native_id
        or document["target_tape_namespace_id"]
        != document["native_occurrence"]["target_tape_namespace_id"]
        or document["observer_control_closure_id"] != closure["control_closure_id"]
        or document["observer_reconciliation_id"] != closure["reconciliation_id"]
        or document["row_acquisition_ids"]
        != [item["row_acquisition_id"] for item in acquisitions]
        or document["requested_row_count"] != 6
        or document["cap_blocked_row_count"] != 1
        or document["support_discovery_draw_count"] != 384
        or document["requested_validation_draw_count"] != 12_288
        or document["total_ground_draw_count"] != 12_672
        or document["ground_access_after_observer_closure"] != 0
        or any(
            document[key] is not expected
            for key, expected in {
                "request_verified_before_namespace_creation": True,
                "namespace_bound_before_ground_access": True,
                "only_requested_rows_executed": True,
                "cap_blocked_rows_not_accessed": True,
                "observer_closed_and_exactly_reconciled": True,
                "fresh_query_ground_recovery_executed": True,
                "immutable_overlay_compiled": False,
                "post_transaction_replanning_performed": False,
                "construction_only": True,
                "plan_certificate_issued": False,
                "campaign_closure_issued": False,
                "official_execution_allowed": False,
            }.items()
        )
    ):
        _fail("recovery ground transaction claims changed")
    payload = dict(document)
    supplied = payload.pop("recovery_eligible_ground_transaction_id")
    for key in (
        "request",
        "namespace_binding",
        "native_occurrence",
        "row_acquisitions",
        "observer_closure",
    ):
        payload.pop(key)
    if supplied != content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_GROUND_TRANSACTION_V1_DOMAIN,
        payload,
    ):
        _fail("recovery ground transaction content ID changed")
    return supplied, tuple(acquisitions), occurrence_id


_REQUEST_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_id",
    "observer_session_public_id",
    "observer_open_binding_id",
    "observer_open_authorization_id",
    "private_reveal_attestation_id",
    "remote_main_anchor_id",
    "target_tape_namespace_id",
    "environment_commitment_id",
    "signer_registry_id",
    "context_id",
    "row_binding_id",
    "catalogue_id",
    "stream_id",
    "pairing_group_id",
    "support_epoch_id",
    "observer_epoch_index",
    "lane",
    "arm",
    "accepted_draw_start",
    "accepted_draw_count",
    "accepted_draw_end",
    "accepted_draw_cap",
    "authority_version",
    "namespace_version",
    "per_draw_record_generation_allowed",
    "request_nonce_allowed",
    "reroll_allowed",
    "private_material_serialized",
    "request_id",
}

_OUTCOME_FIELDS = {
    "schema",
    "schema_version",
    "next_ranks",
    "failure",
    "terminal",
    "spawn_cell",
    "spawn_rank",
    "realized_row_reward",
    "outcome_id",
    "count",
    "reward_sum",
}

_BATCH_FIELDS = {
    "schema",
    "schema_version",
    "profile_key",
    "request_id",
    "occurrence_id",
    "observer_session_public_id",
    "observer_open_binding_id",
    "observer_open_authorization_id",
    "private_reveal_attestation_id",
    "remote_main_anchor_id",
    "target_tape_namespace_id",
    "environment_commitment_id",
    "context_id",
    "row_binding_id",
    "stream_id",
    "arm",
    "observer_epoch_index",
    "accepted_draw_start",
    "accepted_draw_count",
    "accepted_draw_end",
    "accepted_draw_cap",
    "outcome_aggregate_ids",
    "outcome_aggregate_commitments",
    "reward_sum",
    "failure_count",
    "terminal_count",
    "random_word_count",
    "rejection_count",
    "first_random_word_index",
    "next_random_word_index",
    "transcript_commitment",
    "transcript_scheme",
    "rsa_signatures_per_batch",
    "per_draw_records_created",
    "per_draw_records_serialized",
    "individual_random_words_retained",
    "individual_random_words_serialized",
    "private_law_serialized",
    "private_salt_serialized",
    "private_kernel_serialized",
    "request",
    "outcomes",
    "observer_signature_hex",
    "observer_signature_verified",
    "batch_id",
}


def _verify_batch(document: dict[str, Any]) -> tuple[str, tuple[dict[str, Any], ...]]:
    _exact(document, _BATCH_FIELDS, "signed validation batch")
    request = document["request"]
    _exact(request, _REQUEST_FIELDS, "validation batch request")
    request_payload = dict(request)
    request_id = request_payload.pop("request_id")
    if request_id != _raw_id(_BATCH_REQUEST_DOMAIN, request_payload):
        _fail("validation batch request content ID changed")
    outcomes = document["outcomes"]
    if type(outcomes) is not list or not outcomes:
        _fail("validation batch outcomes are absent")
    accepted = failure = terminal = 0
    reward = Fraction(0)
    commitments = []
    outcome_ids = []
    for outcome in outcomes:
        _exact(outcome, _OUTCOME_FIELDS, "validation outcome aggregate")
        identity = {
            key: outcome[key]
            for key in (
                "schema",
                "schema_version",
                "next_ranks",
                "failure",
                "terminal",
                "spawn_cell",
                "spawn_rank",
                "realized_row_reward",
            )
        }
        outcome_id = _raw_id(_BATCH_OUTCOME_DOMAIN, identity)
        count = outcome["count"]
        realized = _fraction(outcome["realized_row_reward"], "outcome reward")
        reward_sum = _fraction(outcome["reward_sum"], "outcome reward sum")
        if (
            outcome["outcome_id"] != outcome_id
            or type(count) is not int
            or count <= 0
            or reward_sum != realized * count
        ):
            _fail("validation outcome aggregate semantics changed")
        accepted += count
        failure += count if outcome["failure"] else 0
        terminal += count if outcome["terminal"] else 0
        reward += reward_sum
        outcome_ids.append(outcome_id)
        commitments.append(
            {
                "outcome_id": outcome_id,
                "count": count,
                "reward_sum": outcome["reward_sum"],
            }
        )
    flattened_pairs = {
        "request_id": request_id,
        "occurrence_id": request["occurrence_id"],
        "observer_session_public_id": request["observer_session_public_id"],
        "observer_open_binding_id": request["observer_open_binding_id"],
        "observer_open_authorization_id": request["observer_open_authorization_id"],
        "private_reveal_attestation_id": request["private_reveal_attestation_id"],
        "remote_main_anchor_id": request["remote_main_anchor_id"],
        "target_tape_namespace_id": request["target_tape_namespace_id"],
        "environment_commitment_id": request["environment_commitment_id"],
        "context_id": request["context_id"],
        "row_binding_id": request["row_binding_id"],
        "stream_id": request["stream_id"],
        "arm": request["arm"],
        "observer_epoch_index": request["observer_epoch_index"],
        "accepted_draw_start": request["accepted_draw_start"],
        "accepted_draw_count": request["accepted_draw_count"],
        "accepted_draw_end": request["accepted_draw_end"],
        "accepted_draw_cap": request["accepted_draw_cap"],
    }
    if (
        any(document[key] != value for key, value in flattened_pairs.items())
        or request["lane"] != "VALIDATION"
        or request["arm"] != "NO_PRIOR"
        or request["observer_epoch_index"] != 1
        or request["accepted_draw_start"] != 1
        or request["accepted_draw_count"] != 2_048
        or request["accepted_draw_end"] != 2_048
        or request["accepted_draw_cap"] != 2_048
        or request["per_draw_record_generation_allowed"] is not False
        or request["request_nonce_allowed"] is not False
        or request["reroll_allowed"] is not False
        or request["private_material_serialized"] is not False
        or accepted != 2_048
        or document["outcome_aggregate_ids"] != outcome_ids
        or document["outcome_aggregate_commitments"] != commitments
        or _fraction(document["reward_sum"], "batch reward sum") != reward
        or document["failure_count"] != failure
        or document["terminal_count"] != terminal
        or document["random_word_count"] != 2_048
        or document["rejection_count"] != 0
        or document["first_random_word_index"] != 1
        or document["next_random_word_index"] != 2_049
        or document["transcript_scheme"]
        != "SHA256_DOMAIN_SEPARATED_ORDERED_SAMPLE_HASH_CHAIN_V2"
        or document["rsa_signatures_per_batch"] != 1
        or document["observer_signature_verified"] is not True
        or any(
            document[key] is not False
            for key in (
                "per_draw_records_created",
                "per_draw_records_serialized",
                "individual_random_words_retained",
                "individual_random_words_serialized",
                "private_law_serialized",
                "private_salt_serialized",
                "private_kernel_serialized",
            )
        )
    ):
        _fail("signed validation batch aggregate semantics changed")
    batch_payload = dict(document)
    supplied = batch_payload.pop("batch_id")
    batch_payload.pop("request")
    batch_payload.pop("outcomes")
    if supplied != _raw_id(_BATCH_DOMAIN, batch_payload):
        _fail("signed validation batch content ID changed")
    return supplied, tuple(outcomes)


def _verify_overlay_and_result(
    document: dict[str, Any],
    *,
    checkpoint_id: str,
    transaction_id: str,
    acquisitions: tuple[dict[str, Any], ...],
    logical_occurrence_id: str,
    source_model: planning_v2.V075NumericalModelV2,
    source_proof: planning_v2.V075NumericalPlanningProofV2,
) -> tuple[str, planning_v2.V075NumericalModelV2, planning_v2.V075NumericalPlanningProofV2]:
    nested = {"validation_deltas", "successor_model", "successor_proof"}
    fields = {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "logical_occurrence_id",
        "recovery_eligible_checkpoint_id",
        "recovery_eligible_query_id",
        "recovery_eligible_recovery_request_id",
        "ground_transaction_id",
        "source_numerical_model_id",
        "source_numerical_proof_id",
        "source_frontier_id",
        "validation_delta_ids",
        "successor_numerical_model_id",
        "successor_numerical_proof_id",
        "successor_outcome",
        "successor_frontier_id",
        "requested_row_count",
        "cap_blocked_row_count",
        "changed_row_count",
        "preserved_row_count",
        "changed_semantic_row_binding_ids",
        "preserved_semantic_row_binding_ids",
        "support_discovery_draw_count",
        "added_signed_validation_draw_count",
        "total_local_ground_draw_count",
        "cached_proof_reused_before_failure",
        "failed_proof_frontier_selected_before_ground_access",
        "only_preregistered_requestable_rows_acquired",
        "cap_blocked_row_remained_unaccessed",
        "signed_batch_deltas_exactly_replayed",
        "old_support_frozen_and_reused",
        "unseen_delta_outcomes_projected_to_other",
        "unrequested_rows_byte_identical",
        "immutable_query_local_model_compiled",
        "same_multistep_query_replanned",
        "horizon",
        "ground_access_after_closed_transaction",
        "fresh_query_recovery_loop_closed_through_replanning",
        "proof_still_failed",
        "next_required_action",
        "plan_certificate_issued",
        "campaign_closure_issued",
        "official_execution_allowed",
        *nested,
        "recovery_eligible_world_model_loop_id",
    }
    _exact(document, fields, "recovery-eligible world-model loop")
    try:
        target_model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(document["successor_model"])
        )
        target_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(document["successor_proof"])
        )
    except (TypeError, ValueError) as error:
        raise ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error(
            "successor numerical model or proof is invalid"
        ) from error
    source_rows = {item.row_id: item.to_document() for item in source_model.rows}
    source_by_binding = {
        item.row_binding_id: item.to_document() for item in source_model.rows
    }
    target_by_binding = {
        item.row_binding_id: item.to_document() for item in target_model.rows
    }
    if set(source_by_binding) != set(target_by_binding):
        _fail("successor model changed the reusable row binding closure")
    deltas = document["validation_deltas"]
    if type(deltas) is not list or len(deltas) != 6:
        _fail("validation delta inventory changed")
    changed = []
    delta_ids = []
    for delta, acquisition in zip(deltas, acquisitions, strict=True):
        delta_fields = {
            "schema",
            "schema_version",
            "profile_key",
            "source_numerical_model_id",
            "source_numerical_row_id",
            "semantic_row_binding_id",
            "source_validation_draw_count",
            "additional_validation_draw_count",
            "target_validation_draw_count",
            "signed_validation_batch_id",
            "independent_validation_stream_starts_at_one",
            "support_expansion_allowed",
            "unseen_outcomes_project_to_other",
            "query_provenance_projected_out_of_successor_model",
            "signed_validation_batch",
            "delta_id",
        }
        _exact(delta, delta_fields, "query-bound validation delta")
        batch_id, outcomes = _verify_batch(delta["signed_validation_batch"])
        source_row = source_rows.get(delta["source_numerical_row_id"])
        target_row = target_by_binding.get(delta["semantic_row_binding_id"])
        if source_row is None or target_row is None:
            _fail("validation delta names an unknown model row")
        if (
            delta["source_numerical_model_id"] != source_model.model_id
            or delta["semantic_row_binding_id"] != source_row["row_binding_id"]
            or delta["source_validation_draw_count"]
            != source_row["validation_draw_count"]
            or delta["additional_validation_draw_count"] != 2_048
            or delta["target_validation_draw_count"]
            != source_row["validation_draw_count"] + 2_048
            or delta["signed_validation_batch_id"] != batch_id
            or delta["independent_validation_stream_starts_at_one"] is not True
            or delta["support_expansion_allowed"] is not False
            or delta["unseen_outcomes_project_to_other"] is not True
            or delta["query_provenance_projected_out_of_successor_model"] is not True
            or acquisition["numerical_row_id"] != delta["source_numerical_row_id"]
            or acquisition["semantic_row_binding_id"]
            != delta["semantic_row_binding_id"]
            or acquisition["validation_batch_id"] != batch_id
        ):
            _fail("validation delta crossed its acquisition or source row")
        payload = dict(delta)
        supplied = payload.pop("delta_id")
        payload.pop("signed_validation_batch")
        if supplied != _raw_id(_DELTA_DOMAIN, payload):
            _fail("validation delta content ID changed")
        support = {
            (
                tuple(item["next_ranks"]),
                item["failure"],
                item["terminal"],
            ): item["descriptor_id"]
            for item in source_row["support"]
        }
        expected_counts = {
            item["event_key"]: item["success_count"]
            for item in source_row["intervals"]
        }
        for outcome in outcomes:
            key = (
                tuple(outcome["next_ranks"]),
                outcome["failure"],
                outcome["terminal"],
            )
            event_key = support.get(key, "OTHER")
            expected_counts[event_key] += outcome["count"]
        target_counts = {
            item["event_key"]: item["success_count"]
            for item in target_row["intervals"]
        }
        source_stable = dict(source_row)
        target_stable = dict(target_row)
        for key in ("row_id", "interval_ids", "intervals", "validation_draw_count"):
            source_stable.pop(key)
            target_stable.pop(key)
        if (
            target_stable != source_stable
            or target_row["support"] != source_row["support"]
            or target_row["validation_draw_count"]
            != delta["target_validation_draw_count"]
            or target_counts != expected_counts
            or any(
                item["draw_count"] != delta["target_validation_draw_count"]
                for item in target_row["intervals"]
            )
        ):
            _fail("successor row is not the exact frozen-support count overlay")
        changed.append(delta["semantic_row_binding_id"])
        delta_ids.append(supplied)
    changed = sorted(changed)
    preserved = sorted(set(source_by_binding) - set(changed))
    if (
        len(changed) != len(set(changed))
        or len(preserved) != 12
        or any(target_by_binding[key] != source_by_binding[key] for key in preserved)
    ):
        _fail("unrequested successor rows changed")
    source_model_document = source_model.to_document()
    target_model_document = target_model.to_document()
    source_model_stable = dict(source_model_document)
    target_model_stable = dict(target_model_document)
    for key in ("rows", "row_ids", "model_id"):
        source_model_stable.pop(key)
        target_model_stable.pop(key)
    recomputed_proof = planning_v2.plan_v075_construction_numerical_model_v2(
        model=target_model,
        route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
    )
    frontier = target_proof.failed_frontier
    if (
        source_model_stable != target_model_stable
        or target_proof.model != target_model
        or canonical_json_bytes(recomputed_proof.to_document())
        != canonical_json_bytes(target_proof.to_document())
        or frontier is None
        or len(frontier.obligations) != 7
        or document["logical_occurrence_id"] != logical_occurrence_id
        or document["recovery_eligible_checkpoint_id"] != checkpoint_id
        or document["ground_transaction_id"] != transaction_id
        or document["source_numerical_model_id"] != source_model.model_id
        or document["source_numerical_proof_id"] != source_proof.proof_id
        or document["source_frontier_id"]
        != source_proof.failed_frontier.frontier_id
        or document["validation_delta_ids"] != delta_ids
        or document["successor_numerical_model_id"] != target_model.model_id
        or document["successor_numerical_proof_id"] != target_proof.proof_id
        or document["successor_outcome"] != "FAILED_PROOF_FRONTIER"
        or document["successor_frontier_id"] != frontier.frontier_id
        or document["requested_row_count"] != 6
        or document["cap_blocked_row_count"] != 1
        or document["changed_row_count"] != 6
        or document["preserved_row_count"] != 12
        or document["changed_semantic_row_binding_ids"] != changed
        or document["preserved_semantic_row_binding_ids"] != preserved
        or document["support_discovery_draw_count"] != 384
        or document["added_signed_validation_draw_count"] != 12_288
        or document["total_local_ground_draw_count"] != 12_672
        or document["horizon"] != 2
        or document["ground_access_after_closed_transaction"] != 0
        or document["proof_still_failed"] is not True
        or document["next_required_action"] != "ROUTE_TO_DIRECT_GROUND_FALLBACK"
        or any(
            document[key] is not expected
            for key, expected in {
                "cached_proof_reused_before_failure": True,
                "failed_proof_frontier_selected_before_ground_access": True,
                "only_preregistered_requestable_rows_acquired": True,
                "cap_blocked_row_remained_unaccessed": True,
                "signed_batch_deltas_exactly_replayed": True,
                "old_support_frozen_and_reused": True,
                "unseen_delta_outcomes_projected_to_other": True,
                "unrequested_rows_byte_identical": True,
                "immutable_query_local_model_compiled": True,
                "same_multistep_query_replanned": True,
                "fresh_query_recovery_loop_closed_through_replanning": True,
                "plan_certificate_issued": False,
                "campaign_closure_issued": False,
                "official_execution_allowed": False,
            }.items()
        )
    ):
        _fail("world-model loop result or exact failed proof changed")
    payload = dict(document)
    supplied = payload.pop("recovery_eligible_world_model_loop_id")
    for key in nested:
        payload.pop(key)
    if supplied != content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_WORLD_MODEL_LOOP_V1_DOMAIN,
        payload,
    ):
        _fail("world-model loop content ID changed")
    return supplied, target_model, target_proof


def verify_recovery_eligible_world_model_loop_bytes_v1(
    *,
    checkpoint_bytes: bytes,
    ground_transaction_bytes: bytes,
    world_model_loop_bytes: bytes,
) -> dict[str, Any]:
    """Independently replay one portable construction loop from bytes."""

    checkpoint_document = _load(checkpoint_bytes, "recovery-eligible checkpoint")
    transaction_document = _load(
        ground_transaction_bytes, "recovery-eligible ground transaction"
    )
    result_document = _load(world_model_loop_bytes, "world-model loop result")
    checkpoint_id, source_model, source_proof = _verify_checkpoint(
        checkpoint_document
    )
    transaction_id, acquisitions, logical_occurrence_id = _verify_transaction(
        transaction_document,
        checkpoint_id=checkpoint_id,
        model=source_model,
        proof=source_proof,
        source_logical_occurrence_id=checkpoint_document[
            "source_logical_occurrence_id"
        ],
    )
    result_id, target_model, target_proof = _verify_overlay_and_result(
        result_document,
        checkpoint_id=checkpoint_id,
        transaction_id=transaction_id,
        acquisitions=acquisitions,
        logical_occurrence_id=logical_occurrence_id,
        source_model=source_model,
        source_proof=source_proof,
    )
    payload = {
        "schema": "acfqp.construction_k7_recovery_eligible_world_model_loop_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "recovery_eligible_checkpoint_id": checkpoint_id,
        "logical_occurrence_id": logical_occurrence_id,
        "ground_transaction_id": transaction_id,
        "world_model_loop_id": result_id,
        "source_numerical_model_id": source_model.model_id,
        "source_numerical_proof_id": source_proof.proof_id,
        "successor_numerical_model_id": target_model.model_id,
        "successor_numerical_proof_id": target_proof.proof_id,
        "independently_recomputed_source_h2_proof": True,
        "independently_recomputed_successor_h2_proof": True,
        "validation_batch_content_ids_recomputed": True,
        "validation_aggregate_counts_reconciled": True,
        "immutable_overlay_independently_replayed": True,
        "unrequested_rows_byte_identical": True,
        "proof_still_failed": True,
        "verified_next_route": "DIRECT_GROUND_FALLBACK",
        "portable_discovery_batch_replay_present": False,
        "observer_rsa_signature_independently_reverified": False,
        "compact_observer_closure_summary_only": True,
        "verification_lane": "EVALUATION",
        "verification_work_included_in_operational_route_work": False,
        "plan_certificate_verified": False,
        "official_execution_allowed": False,
        "valid": True,
    }
    return {
        **payload,
        "verification_id": content_id(VERIFICATION_DOMAIN, payload),
    }


__all__ = [
    "ConstructionK7RecoveryEligibleWorldModelLoopIndependentVerifierV1Error",
    "verify_recovery_eligible_world_model_loop_bytes_v1",
]
