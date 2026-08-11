"""Bytes-only verifier for a reusable query-bound RAPM and fresh query.

The verifier does not import the producer.  It independently reconstructs the
portable numerical model, replans the claimed adaptive proof, replays all
three content-addressed documents, and keeps the source-acquisition and
persistent-proof-DAG limitations explicit.
"""

from __future__ import annotations

from typing import Any, NoReturn

from acfqp import v075_batch_native_planning_backend_v2 as planning_v2
from acfqp import v075_registered_occurrence_worker_v1 as worker_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_VERIFICATION_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.106"
PROFILE_KEY = "construction_k7_query_bound_reusable_rapm_snapshot_v1"

SNAPSHOT_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SNAPSHOT_V1_DOMAIN
QUERY_SPEC_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_SPEC_V1_DOMAIN
QUERY_RESULT_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_QUERY_RESULT_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("reusable RAPM verification domain is not central")


class ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
    ValueError
):
    """The snapshot, fresh query, or exact proof replay diverged."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _load(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


_SNAPSHOT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_operational_trace_id",
    "source_logical_occurrence_id",
    "source_reusable_abstract_query_id",
    "source_final_local_replanning_id",
    "transaction_1_replanning_id",
    "transaction_2_recovery_request_id",
    "transaction_2_ground_transaction_id",
    "source_numerical_model_id",
    "source_numerical_proof_id",
    "source_frontier_id",
    "reusable_numerical_model_id",
    "reusable_numerical_proof_id",
    "reusable_frontier_id",
    "changed_semantic_row_binding_ids",
    "preserved_semantic_row_binding_ids",
    "reusable_row_count",
    "changed_row_count",
    "preserved_row_count",
    "source_validation_draw_count_on_changed_rows",
    "added_signed_validation_draw_count",
    "reusable_validation_draw_count_on_changed_rows",
    "cumulative_local_ground_draw_count",
    "source_local_transaction_count",
    "query_neutral_numerical_model_present",
    "portable_exact_replanning_proof_present",
    "query_provenance_projected_out_of_model",
    "source_occurrence_bundle_binding_present",
    "portable_source_ground_transaction_replay_present",
    "fresh_query_ground_access_authority_present",
    "persistent_proof_dependency_dag_present",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "reusable_model",
    "reusable_proof",
    "query_bound_reusable_rapm_snapshot_id",
}

_QUERY_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "reusable_rapm_snapshot_id",
    "reusable_numerical_model_id",
    "source_logical_occurrence_id",
    "logical_occurrence_id",
    "query_ordinal",
    "threshold_profile_id",
    "route",
    "fresh_logical_occurrence",
    "ground_input_parameter_present",
    "observer_or_signer_input_present",
    "model_construction_repeated",
    "query_bound_reusable_rapm_query_id",
}

_RESULT_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "reusable_rapm_snapshot_id",
    "reusable_rapm_query_id",
    "source_logical_occurrence_id",
    "logical_occurrence_id",
    "reusable_numerical_model_id",
    "numerical_proof_id",
    "numerical_outcome",
    "policy_id",
    "failed_frontier_id",
    "fresh_logical_occurrence",
    "snapshot_model_reused",
    "model_construction_repeated",
    "new_ground_access_count",
    "ground_input_parameter_present",
    "observer_or_signer_input_present",
    "exact_abstract_replanning_completed",
    "certificate_failed_frontier_present",
    "query_local_ground_recovery_authorized_here",
    "query_local_ground_recovery_executed_here",
    "plan_certificate_issued",
    "campaign_closure_issued",
    "official_execution_allowed",
    "next_required_action",
    "query",
    "numerical_proof",
    "query_bound_reusable_rapm_query_result_id",
}


def _verify_snapshot(
    raw: bytes,
) -> tuple[dict[str, Any], planning_v2.V075NumericalModelV2]:
    document = _load(raw, "reusable RAPM snapshot")
    require_exact_fields(
        document,
        _SNAPSHOT_FIELDS,
        context="reusable RAPM snapshot",
    )
    if (
        document["schema"]
        != "acfqp.construction_k7_query_bound_reusable_rapm_snapshot.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"]
        != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
    ):
        _fail("reusable RAPM snapshot profile changed")
    for key in (
        "source_operational_trace_id",
        "source_logical_occurrence_id",
        "source_reusable_abstract_query_id",
        "source_final_local_replanning_id",
        "transaction_1_replanning_id",
        "transaction_2_recovery_request_id",
        "transaction_2_ground_transaction_id",
        "source_numerical_model_id",
        "source_numerical_proof_id",
        "source_frontier_id",
        "reusable_numerical_model_id",
        "reusable_numerical_proof_id",
        "reusable_frontier_id",
    ):
        _cid(document[key], key)
    expected_claims = {
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
    if any(document[key] != value for key, value in expected_claims.items()):
        _fail("reusable RAPM snapshot claim locks changed")
    try:
        model = planning_v2.replay_v075_numerical_model_bytes_v2(
            canonical_json_bytes(document["reusable_model"])
        )
        proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(document["reusable_proof"])
        )
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
            "reusable RAPM model/proof failed typed replay"
        ) from error
    frontier = proof.failed_frontier
    if (
        proof.model != model
        or proof.route is not planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT
        or proof.outcome
        is not planning_v2.V075NumericalOutcomeV2.FAILED_FRONTIER
        or frontier is None
        or document["reusable_numerical_model_id"] != model.model_id
        or document["reusable_numerical_proof_id"] != proof.proof_id
        or document["reusable_frontier_id"] != frontier.frontier_id
    ):
        _fail("reusable RAPM model/proof identity graph changed")
    changed = document["changed_semantic_row_binding_ids"]
    preserved = document["preserved_semantic_row_binding_ids"]
    row_bindings = sorted(item.row_binding_id for item in model.rows)
    if (
        type(changed) is not list
        or type(preserved) is not list
        or changed != sorted(set(changed))
        or preserved != sorted(set(preserved))
        or not changed
        or set(changed).intersection(preserved)
        or sorted((*changed, *preserved)) != row_bindings
        or document["reusable_row_count"] != len(model.rows)
        or document["changed_row_count"] != len(changed)
        or document["preserved_row_count"] != len(preserved)
    ):
        _fail("reusable RAPM row partition changed")
    counts = (
        document["source_validation_draw_count_on_changed_rows"],
        document["added_signed_validation_draw_count"],
        document["reusable_validation_draw_count_on_changed_rows"],
        document["cumulative_local_ground_draw_count"],
    )
    if (
        any(type(value) is not int or value <= 0 for value in counts)
        or counts[0] + counts[1] != counts[2]
    ):
        _fail("reusable RAPM draw accounting changed")
    payload = dict(document)
    snapshot_id = payload.pop("query_bound_reusable_rapm_snapshot_id")
    payload.pop("reusable_model")
    payload.pop("reusable_proof")
    if snapshot_id != content_id(SNAPSHOT_DOMAIN, payload):
        _fail("reusable RAPM snapshot content ID changed")
    return document, model


def _verify_query(
    document: Any,
    *,
    snapshot: dict[str, Any],
) -> tuple[dict[str, Any], str]:
    if type(document) is not dict:
        _fail("reusable RAPM query is absent")
    require_exact_fields(
        document,
        _QUERY_FIELDS,
        context="reusable RAPM query",
    )
    if (
        document["schema"]
        != "acfqp.construction_k7_query_bound_reusable_rapm_query_spec.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"]
        != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PROFILE_KEY
        or document["reusable_rapm_snapshot_id"]
        != snapshot["query_bound_reusable_rapm_snapshot_id"]
        or document["reusable_numerical_model_id"]
        != snapshot["reusable_numerical_model_id"]
        or document["source_logical_occurrence_id"]
        != snapshot["source_logical_occurrence_id"]
        or document["logical_occurrence_id"]
        == document["source_logical_occurrence_id"]
        or type(document["query_ordinal"]) is not int
        or document["query_ordinal"] <= 0
        or document["threshold_profile_id"]
        != worker_v1.V075WorkerThresholdProfileV1().threshold_profile_id
        or document["route"] != "ADAPTIVE_QUOTIENT"
        or document["fresh_logical_occurrence"] is not True
        or document["ground_input_parameter_present"] is not False
        or document["observer_or_signer_input_present"] is not False
        or document["model_construction_repeated"] is not False
    ):
        _fail("reusable RAPM fresh-query contract changed")
    for key in (
        "reusable_rapm_snapshot_id",
        "reusable_numerical_model_id",
        "source_logical_occurrence_id",
        "logical_occurrence_id",
        "threshold_profile_id",
    ):
        _cid(document[key], key)
    payload = dict(document)
    query_id = payload.pop("query_bound_reusable_rapm_query_id")
    if query_id != content_id(QUERY_SPEC_DOMAIN, payload):
        _fail("reusable RAPM query content ID changed")
    return document, query_id


def verify_query_bound_reusable_rapm_bundle_bytes_v1(
    *,
    snapshot_bytes: bytes,
    result_bytes: bytes,
) -> dict[str, Any]:
    snapshot, model = _verify_snapshot(snapshot_bytes)
    result = _load(result_bytes, "reusable RAPM query result")
    require_exact_fields(
        result,
        _RESULT_FIELDS,
        context="reusable RAPM query result",
    )
    query, query_id = _verify_query(result["query"], snapshot=snapshot)
    if (
        result["schema"]
        != "acfqp.construction_k7_query_bound_reusable_rapm_query_result.v1"
        or result["schema_version"] != SCHEMA_VERSION
        or result["proposed_contract_version"]
        != PROPOSED_CONTRACT_VERSION
        or result["profile_key"] != PROFILE_KEY
    ):
        _fail("reusable RAPM query-result profile changed")
    try:
        claimed_proof = planning_v2.replay_v075_numerical_proof_bytes_v2(
            canonical_json_bytes(result["numerical_proof"])
        )
        exact_proof = planning_v2.plan_v075_construction_numerical_model_v2(
            model=model,
            route=planning_v2.V075PlanningRouteV2.ADAPTIVE_QUOTIENT,
        )
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error(
            "fresh reusable RAPM proof failed exact replanning"
        ) from error
    frontier = exact_proof.failed_frontier
    policy = exact_proof.policy
    if (
        claimed_proof.canonical_bytes != exact_proof.canonical_bytes
        or frontier is None
        or result["reusable_rapm_snapshot_id"]
        != snapshot["query_bound_reusable_rapm_snapshot_id"]
        or result["reusable_rapm_query_id"] != query_id
        or result["source_logical_occurrence_id"]
        != query["source_logical_occurrence_id"]
        or result["logical_occurrence_id"] != query["logical_occurrence_id"]
        or result["reusable_numerical_model_id"] != model.model_id
        or result["numerical_proof_id"] != exact_proof.proof_id
        or result["numerical_outcome"] != exact_proof.outcome.value
        or result["policy_id"]
        != (None if policy is None else policy.policy_id)
        or result["failed_frontier_id"] != frontier.frontier_id
    ):
        _fail("fresh reusable RAPM proof identity graph changed")
    expected_claims = {
        "fresh_logical_occurrence": True,
        "snapshot_model_reused": True,
        "model_construction_repeated": False,
        "new_ground_access_count": 0,
        "ground_input_parameter_present": False,
        "observer_or_signer_input_present": False,
        "exact_abstract_replanning_completed": True,
        "certificate_failed_frontier_present": True,
        "query_local_ground_recovery_authorized_here": False,
        "query_local_ground_recovery_executed_here": False,
        "plan_certificate_issued": False,
        "campaign_closure_issued": False,
        "official_execution_allowed": False,
        "next_required_action": "QUERY_LOCAL_CERTIFICATE_FRONTIER_RESOLUTION",
    }
    if any(result[key] != value for key, value in expected_claims.items()):
        _fail("fresh reusable RAPM query-result claim locks changed")
    payload = dict(result)
    result_id = payload.pop("query_bound_reusable_rapm_query_result_id")
    payload.pop("query")
    payload.pop("numerical_proof")
    if result_id != content_id(QUERY_RESULT_DOMAIN, payload):
        _fail("fresh reusable RAPM query-result content ID changed")
    verification_payload = {
        "schema": "acfqp.construction_k7_query_bound_reusable_rapm_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "reusable_rapm_snapshot_id": snapshot[
            "query_bound_reusable_rapm_snapshot_id"
        ],
        "reusable_rapm_query_id": query_id,
        "reusable_rapm_query_result_id": result_id,
        "source_logical_occurrence_id": query[
            "source_logical_occurrence_id"
        ],
        "logical_occurrence_id": query["logical_occurrence_id"],
        "reusable_numerical_model_id": model.model_id,
        "numerical_proof_id": exact_proof.proof_id,
        "failed_frontier_id": frontier.frontier_id,
        "reusable_row_count": len(model.rows),
        "changed_row_count": snapshot["changed_row_count"],
        "preserved_row_count": snapshot["preserved_row_count"],
        "snapshot_model_and_proof_typed_replay": True,
        "fresh_query_exact_abstract_replanning": True,
        "new_ground_access_count": 0,
        "source_ground_transaction_replay_performed": False,
        "source_occurrence_bundle_binding_verified": False,
        "persistent_proof_dependency_dag_verified": False,
        "plan_certificate_verified": False,
        "official_execution_allowed": False,
        "verification_result": "DURABLE_REUSABLE_RAPM_AND_FRESH_QUERY_VERIFIED",
        "next_required_action": (
            "BIND_SOURCE_BUNDLE_AND_INCREMENTAL_PROOF_DEPENDENCY_DAG"
        ),
    }
    return {
        **verification_payload,
        "query_bound_reusable_rapm_verification_id": content_id(
            VERIFICATION_DOMAIN,
            verification_payload,
        ),
    }


__all__ = [
    "ConstructionK7QueryBoundReusableRAPMIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "verify_query_bound_reusable_rapm_bundle_bytes_v1",
]
