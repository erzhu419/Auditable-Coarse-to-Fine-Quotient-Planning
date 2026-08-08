"""Fresh-exec structural replay for the H1 predecision current-access cut.

This module is deliberately complementary to the Contract 2.0.57 authority
core.  It owns one isolated, exact-source child and returns broker-observed raw
runtime facts.  It never issues the current-access authority, a route decision,
formal accounting, or a terminal artifact.

The child imports only a fixed standard-library allowlist.  Six immutable
memfds carry the already-issued Contract 2.0.52 structural inputs.  The child
reconstructs the exact current-identity candidate and its verification bytes;
it has no project package, kernel, QuerySpec, proof verifier, planner, J0, or
fallback implementation in its import graph.
"""

from __future__ import annotations

import ast
from dataclasses import InitVar, dataclass, field
from enum import Enum
import fcntl
import hashlib
import hmac
import os
from pathlib import Path
import select
import signal
import socket
import stat
import struct
import subprocess
import tempfile
import threading
import time
from types import MappingProxyType
from typing import Any, Mapping, NoReturn

from acfqp import v075_k7_atomic_pidfd_runtime_v1 as sealed_runtime_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_RUNTIME_UNAVAILABLE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.57"
PROFILE_KEY = "construction_k7_h1_current_access_fresh_exec_runtime_v1"
PYTHON_EXECUTABLE = Path("/usr/bin/python3")
PROCESS_TIMEOUT_SECONDS = 60
MAX_INPUT_BYTES = 16 * 1024 * 1024
MAX_PACKET_BYTES = 2 * 1024 * 1024
VERIFICATION_STATUS = "OBSERVED_RUNTIME_PLUS_EXHAUSTIVE_CAPABILITY_CLOSURE"

INPUT_ROLES = (
    "PREDECISION_CONTEXT",
    "CURRENT_SOURCE_FIXTURE",
    "PROOF_MATCH_ATTESTATION",
    "H1_TWO_ROLE_RECIPE",
    "CURRENT_IDENTITY_CANDIDATE",
    "CANDIDATE_VERIFICATION",
)

FORBIDDEN_OPERATIONS = (
    "DURABLE_PROOF_PRODUCER_OR_VERIFIER",
    "FALLBACK_SOLVER",
    "GROUND_OUTCOME_ENUMERATION",
    "J0_OR_OTHER_PLANNER",
    "KERNEL_STEP",
    "POSTRUN_ARTIFACT_READ",
)

ZERO_CALL_FIELD_BY_OPERATION = MappingProxyType(
    {
        "DURABLE_PROOF_PRODUCER_OR_VERIFIER": "durable_proof_verifier_calls",
        "FALLBACK_SOLVER": "fallback_solver_calls",
        "GROUND_OUTCOME_ENUMERATION": "ground_outcome_enumerations",
        "J0_OR_OTHER_PLANNER": "planner_or_j0_calls",
        "KERNEL_STEP": "kernel_step_calls",
        "POSTRUN_ARTIFACT_READ": "postrun_artifact_reads",
    }
)

_CURRENT_CONTEXT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_current_access_execution_profile_id",
        "h1_current_access_fresh_exec_runtime_profile_id",
        "h1_current_access_fresh_exec_source_manifest_id",
        "h1_current_access_fresh_exec_runtime_manifest_id",
        "h1_current_source_fixture_id",
        "h1_durable_proof_match_attestation_id",
        "h1_direct_fallback_two_role_recipe_id",
        "h1_production_current_identity_candidate_id",
        "h1_production_current_identity_candidate_verification_id",
        "precontext_sealed_inputs",
        "exact_infeasibility_identity_id",
        "structural_id",
        "query_id",
        "BuildEpoch_id",
        "kernel_id",
        "threshold_profile_id",
        "reward_profile_id",
        "policy_class_id",
        "complete_search_profile_id",
        "logical_occurrence_id",
        "route_attempt_id",
        "session_nonce",
        "stage_scope",
        "downstream_route_authority_join_present",
        "h1_current_access_predecision_context_id",
    }
)

_IDENTITY_COORDINATES = (
    "structural_id",
    "query_id",
    "BuildEpoch_id",
    "kernel_id",
    "threshold_profile_id",
    "reward_profile_id",
    "policy_class_id",
    "complete_search_profile_id",
)

_DOMAIN_TEXT = MappingProxyType(
    {
        "context": CONSTRUCTION_K7_H1_CURRENT_ACCESS_PREDECISION_CONTEXT_V1_DOMAIN,
        "build": CONSTRUCTION_K7_H1_CURRENT_BUILD_KERNEL_ATTESTATION_V1_DOMAIN,
        "query": CONSTRUCTION_K7_H1_CURRENT_QUERY_ATTESTATION_V1_DOMAIN,
        "source": CONSTRUCTION_K7_H1_CURRENT_SOURCE_FIXTURE_V1_DOMAIN,
        "proof": CONSTRUCTION_K7_H1_DURABLE_PROOF_MATCH_ATTESTATION_V1_DOMAIN,
        "recipe": CONSTRUCTION_K7_H1_DIRECT_FALLBACK_TWO_ROLE_RECIPE_V1_DOMAIN,
        "candidate": CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_V1_DOMAIN,
        "candidate_verification": (
            CONSTRUCTION_K7_H1_PRODUCTION_CURRENT_IDENTITY_VERIFICATION_V1_DOMAIN
        ),
        "identity": PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN,
        "child_result": CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
    }
)

_PROFILE_ISSUER = object()
_SOURCE_MANIFEST_ISSUER = object()
_RUNTIME_MANIFEST_ISSUER = object()
_UNAVAILABLE_ISSUER = object()
_FACTS_ISSUER = object()
_VERIFICATION_ISSUER = object()
_STATIC_RETENTION: dict[int, tuple[object, bytes]] = {}
_STATIC_RETENTION_LOCK = threading.RLock()


def _retain_static(value: object, raw: bytes) -> None:
    with _STATIC_RETENTION_LOCK:
        if id(value) in _STATIC_RETENTION:
            _fail("fresh-exec prelaunch object was retained twice")
        _STATIC_RETENTION[id(value)] = (value, raw)


def _require_static(value: Any, expected_type: type, label: str) -> Any:
    if type(value) is not expected_type:
        _fail(f"{label} has a foreign type")
    with _STATIC_RETENTION_LOCK:
        retained = _STATIC_RETENTION.get(id(value))
    if retained is None or retained[0] is not value:
        _fail(f"{label} is not one retained prelaunch object")
    if not hmac.compare_digest(retained[1], canonical_json_bytes(value.to_document())):
        _fail(f"{label} changed after prelaunch issuance")
    return value


class ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(RuntimeError):
    """The exact child replay or broker observation failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_INPUT_BYTES:
        _fail(f"{label} must be bounded, nonempty immutable bytes")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one exact canonical object")
    return document


def _embedded_id(
    document: Mapping[str, Any],
    *,
    id_field: str,
    domain: str,
    label: str,
    excluded_fields: tuple[str, ...] = (),
) -> str:
    if type(document) is not dict:
        _fail(f"{label} must be one exact object")
    identifier = _cid(document.get(id_field), label)
    payload = dict(document)
    payload.pop(id_field, None)
    for field_name in excluded_fields:
        payload.pop(field_name, None)
    if not hmac.compare_digest(content_id(domain, payload), identifier):
        _fail(f"{label} content identity did not replay")
    return identifier


def _identity_from_context(context: Mapping[str, Any]) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.phase3e_exact_infeasibility_identity.v1",
        "schema_version": "1.0.0",
        **{name: context[name] for name in _IDENTITY_COORDINATES},
    }
    return {
        **payload,
        "exact_infeasibility_identity_id": content_id(
            PHASE3E_EXACT_INFEASIBILITY_IDENTITY_V1_DOMAIN,
            payload,
        ),
    }


def _candidate_crosswalk(
    identity: Mapping[str, Any], recipe_projection: Mapping[str, Any]
) -> list[dict[str, Any]]:
    recipe_names = {
        "structural_id": "structural_id",
        "query_id": "query_id",
        "BuildEpoch_id": "BuildEpoch_id",
        "kernel_id": "kernel_id",
        "threshold_profile_id": "threshold_profile_id",
    }
    rows: list[dict[str, Any]] = []
    for name in _IDENTITY_COORDINATES:
        recipe_name = recipe_names.get(name)
        recipe_value = (
            None if recipe_name is None else recipe_projection[recipe_name]
        )
        rows.append(
            {
                "coordinate": name,
                "current_value": identity[name],
                "proof_match_value": identity[name],
                "recipe_value": recipe_value,
                "recipe_coordinate_applicable": recipe_value is not None,
            }
        )
    return rows


_ROUTE_FORBIDDEN_DECLARATION = {
    "kind": "FORBIDDEN_API_DECLARATION_NOT_OBSERVED_COUNTERS",
    "forbidden_operations": [
        "DURABLE_PROOF_PRODUCER_OR_VERIFIER",
        "FALLBACK_SOLVER",
        "GROUND_OUTCOME_ENUMERATION",
        "J0_OR_OTHER_PLANNER",
        "KERNEL_STEP",
    ],
    "caller_supplied_zero_counters_accepted": False,
}
_UNOBSERVED_CALLS = {
    "kind": "UNOBSERVED",
    "reason": "OBSERVED_ROUTE_TIME_ACCESS_LOG_PENDING",
}


def _structural_replay(
    raw_by_role: Mapping[str, bytes],
) -> dict[str, Any]:
    if type(raw_by_role) is not dict or tuple(raw_by_role) != INPUT_ROLES:
        _fail("fresh-exec input roles are not exact and ordered")
    documents = {
        role: _canonical_document(raw_by_role[role], role.lower())
        for role in INPUT_ROLES
    }
    context = documents["PREDECISION_CONTEXT"]
    if frozenset(context) != _CURRENT_CONTEXT_FIELDS:
        _fail("predecision context fields are not exact")
    if (
        context.get("schema") != "acfqp.h1_current_access_predecision_context.v1"
        or context.get("schema_version") != SCHEMA_VERSION
        or context.get("proposed_contract_version") != PROPOSED_CONTRACT_VERSION
        or context.get("profile_key")
        != "construction_k7_h1_current_access_authority_v1"
    ):
        _fail("predecision context contract identity is not exact")
    context_id = _embedded_id(
        context,
        id_field="h1_current_access_predecision_context_id",
        domain=_DOMAIN_TEXT["context"],
        label="predecision context",
    )
    if (
        context.get("stage_scope") != "PREDECISION_CURRENT_ACCESS"
        or context.get("downstream_route_authority_join_present") is not False
    ):
        _fail("predecision context crossed the downstream decision boundary")
    for name in (
        "h1_current_access_execution_profile_id",
        "h1_current_access_fresh_exec_runtime_profile_id",
        "h1_current_access_fresh_exec_source_manifest_id",
        "h1_current_access_fresh_exec_runtime_manifest_id",
        "h1_current_source_fixture_id",
        "h1_durable_proof_match_attestation_id",
        "h1_direct_fallback_two_role_recipe_id",
        "h1_production_current_identity_candidate_id",
        "h1_production_current_identity_candidate_verification_id",
        "exact_infeasibility_identity_id",
        *_IDENTITY_COORDINATES,
        "logical_occurrence_id",
        "route_attempt_id",
    ):
        _cid(context.get(name), name)
    nonce = context.get("session_nonce")
    if (
        type(nonce) is not str
        or len(nonce) != 64
        or any(character not in "0123456789abcdef" for character in nonce)
    ):
        _fail("predecision session nonce is not exact")

    source = documents["CURRENT_SOURCE_FIXTURE"]
    build = source.get("build_kernel_attestation")
    query = source.get("query_attestation")
    if type(build) is not dict or type(query) is not dict:
        _fail("current-source nested attestations are absent")
    build_id = _embedded_id(
        build,
        id_field="build_kernel_attestation_id",
        domain=_DOMAIN_TEXT["build"],
        label="build/kernel attestation",
    )
    query_id = _embedded_id(
        query,
        id_field="query_attestation_id",
        domain=_DOMAIN_TEXT["query"],
        label="query attestation",
    )
    source_id = _embedded_id(
        source,
        id_field="current_source_fixture_id",
        domain=_DOMAIN_TEXT["source"],
        label="current-source fixture",
        excluded_fields=("build_kernel_attestation", "query_attestation"),
    )
    if (
        source.get("build_kernel_attestation_id") != build_id
        or source.get("query_attestation_id") != query_id
        or context["h1_current_source_fixture_id"] != source_id
    ):
        _fail("current-source nested identity chain crossed")

    proof = documents["PROOF_MATCH_ATTESTATION"]
    proof_id = _embedded_id(
        proof,
        id_field="proof_match_attestation_id",
        domain=_DOMAIN_TEXT["proof"],
        label="proof-match attestation",
    )
    recipe = documents["H1_TWO_ROLE_RECIPE"]
    recipe_id = _embedded_id(
        recipe,
        id_field="h1_direct_fallback_two_role_recipe_id",
        domain=_DOMAIN_TEXT["recipe"],
        label="H1 recipe",
    )
    if context["h1_durable_proof_match_attestation_id"] != proof_id:
        _fail("proof-match context binding crossed")

    identity = _identity_from_context(context)
    recipe_projection = recipe.get("legacy_h1_preexecution_projection")
    if type(recipe_projection) is not dict:
        _fail("H1 recipe lacks its legacy structural projection")
    if (
        identity["exact_infeasibility_identity_id"]
        != context["exact_infeasibility_identity_id"]
        or source.get("identity") != identity
        or proof.get("current_source_fixture_id") != source_id
        or proof.get("h1_direct_fallback_two_role_recipe_id") != recipe_id
        or proof.get("exact_infeasibility_identity_id")
        != identity["exact_infeasibility_identity_id"]
        or recipe_projection.get("exact_infeasibility_identity_id")
        != identity["exact_infeasibility_identity_id"]
        or any(
            recipe_projection.get(name) != identity[name]
            for name in (
                "structural_id",
                "query_id",
                "BuildEpoch_id",
                "kernel_id",
                "threshold_profile_id",
            )
        )
        or recipe_projection.get("selected_plan_id")
        != proof.get("selected_plan_id")
        or recipe_projection.get("logical_occurrence_id")
        != context["logical_occurrence_id"]
        or recipe_projection.get("route_attempt_id")
        != context["route_attempt_id"]
    ):
        _fail("current source, proof match, recipe, or context crossed identity")

    candidate_payload = {
        "schema": "acfqp.construction_k7_h1_production_current_identity_candidate.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.52",
        "profile_key": "construction_k7_h1_production_current_identity_v1",
        "current_source_fixture_id": source_id,
        "build_kernel_attestation_id": build_id,
        "query_attestation_id": query_id,
        "proof_match_attestation_id": proof_id,
        "proof_plan_binding_id": proof["plan_binding"]["cache_consumption_id"],
        "h1_direct_fallback_two_role_recipe_id": recipe_id,
        "preregistered_recipe_chain": proof["preregistered_recipe_chain"],
        "identity": identity,
        "exact_identity_crosswalk": _candidate_crosswalk(
            identity, recipe_projection
        ),
        "source_archive_id": source["source_archive_id"],
        "source_archive_sha256": source["source_archive_sha256"],
        "source_archive_byte_count": source["source_archive_byte_count"],
        "durable_proof_id": proof["durable_proof_id"],
        "durable_proof_verification_id": proof["plan_binding"]["verification_id"],
        "selected_plan_id": recipe_projection["selected_plan_id"],
        "RouteDecisionContext_id": recipe_projection["RouteDecisionContext_id"],
        "decision_point_id": recipe_projection["decision_point_id"],
        "logical_occurrence_id": recipe_projection["logical_occurrence_id"],
        "route_attempt_id": recipe_projection["route_attempt_id"],
        "route_time_forbidden_api_declaration": _ROUTE_FORBIDDEN_DECLARATION,
        "route_time_call_counts": _UNOBSERVED_CALLS,
        "route_time_observed_access_log_id": None,
        "route_time_access_evidence_status": "PENDING_OBSERVED_ACCESS_LOG",
        "current_identity_derived_before_claimant_comparison": True,
        "claimant_fields_accepted_as_current": False,
        "legacy_current_identity_used_as_authority": False,
        "durable_proof_semantics_replayed_at_route_time": False,
        "source_archive_loaded_execution_claimed": False,
        "source_archive_is_live_current_issuer_provenance": False,
        "same_process_unforgeability_claimed": False,
        "private_module_state_adversary_resistance_claimed": False,
        "eligible_as_production_consumer_authority": False,
        "production_consumers_must_reject_candidate": True,
        "production_current_identity_candidate": True,
        "production_current_identity_authority": False,
        "formal_v7_route_authority_present": False,
        "production_execution_authorized": False,
        "official_execution_allowed": False,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "sample_efficiency_gate_status": "SAMPLE_EFFICIENCY_GATE_NOT_RUN",
        "construction_only": True,
    }
    candidate_id = content_id(_DOMAIN_TEXT["candidate"], candidate_payload)
    expected_candidate = {
        **candidate_payload,
        "production_current_identity_candidate_id": candidate_id,
    }
    if documents["CURRENT_IDENTITY_CANDIDATE"] != expected_candidate:
        _fail("Contract 2.0.52 candidate did not replay from source/proof/recipe")

    candidate_raw = raw_by_role["CURRENT_IDENTITY_CANDIDATE"]
    verification_payload = {
        "schema": "acfqp.construction_k7_h1_production_current_identity_candidate_verification.v1",
        "schema_version": "1.0.0",
        "proposed_contract_version": "2.0.52",
        "profile_key": "construction_k7_h1_production_current_identity_v1",
        "production_current_identity_candidate_id": candidate_id,
        "candidate_sha256": _sha(candidate_raw),
        "candidate_byte_count": len(candidate_raw),
        "current_source_fixture_id": source_id,
        "proof_match_attestation_id": proof_id,
        "h1_direct_fallback_two_role_recipe_id": recipe_id,
        "structurally_invokes_durable_proof_verifier": False,
        "structurally_invokes_kernel_or_planner": False,
        "route_time_forbidden_api_declaration": _ROUTE_FORBIDDEN_DECLARATION,
        "route_time_call_counts": _UNOBSERVED_CALLS,
        "route_time_observed_access_log_id": None,
        "route_time_access_evidence_status": "PENDING_OBSERVED_ACCESS_LOG",
        "exact_structural_replay": True,
        "production_current_identity_candidate_verified": True,
        "production_current_identity_authority_verified": False,
        "same_process_unforgeability_verified": False,
        "eligible_as_production_consumer_authority": False,
        "production_consumers_must_reject_candidate": True,
        "production_execution_authorized": False,
        "construction_only": True,
    }
    candidate_verification_id = content_id(
        _DOMAIN_TEXT["candidate_verification"], verification_payload
    )
    expected_verification = {
        **verification_payload,
        "verification_id": candidate_verification_id,
    }
    if documents["CANDIDATE_VERIFICATION"] != expected_verification:
        _fail("Contract 2.0.52 candidate verification did not replay")

    precontext_artifact_ids = (
        source_id,
        proof_id,
        recipe_id,
        candidate_id,
        candidate_verification_id,
    )
    expected_precontext_rows = [
        {
            "role": role,
            "artifact_id": artifact_id,
            "sha256": _sha(raw_by_role[role]),
            "byte_count": len(raw_by_role[role]),
        }
        for role, artifact_id in zip(INPUT_ROLES[1:], precontext_artifact_ids)
    ]
    if (
        context["h1_direct_fallback_two_role_recipe_id"] != recipe_id
        or context["h1_production_current_identity_candidate_id"] != candidate_id
        or context["h1_production_current_identity_candidate_verification_id"]
        != candidate_verification_id
        or context["precontext_sealed_inputs"] != expected_precontext_rows
    ):
        _fail("predecision context did not freeze every precontext input")

    return {
        "context": context,
        "context_id": context_id,
        "identity": identity,
        "source_id": source_id,
        "proof_id": proof_id,
        "recipe_id": recipe_id,
        "candidate_id": candidate_id,
        "candidate_verification_id": candidate_verification_id,
    }


def _sealed_input_rows(
    raw_by_role: Mapping[str, bytes], replay: Mapping[str, Any]
) -> list[dict[str, Any]]:
    artifact_ids = (
        replay["context_id"],
        replay["source_id"],
        replay["proof_id"],
        replay["recipe_id"],
        replay["candidate_id"],
        replay["candidate_verification_id"],
    )
    return [
        {
            "role": role,
            "artifact_id": artifact_id,
            "sha256": _sha(raw_by_role[role]),
            "byte_count": len(raw_by_role[role]),
        }
        for role, artifact_id in zip(INPUT_ROLES, artifact_ids)
    ]


def _require_predecision_input_set(
    value: Any,
    *,
    raw_by_role: Mapping[str, bytes],
    replay: Mapping[str, Any],
    runtime_manifest_id: str,
) -> tuple[str, dict[str, Any]]:
    """Consume the core-owned post-context launch set without circular imports."""

    try:
        from acfqp import construction_k7_h1_current_access_authority_v1 as core_v1
    except ImportError as error:
        raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(
            "current-access predecision input-set authority is unavailable"
        ) from error
    expected_type = getattr(core_v1, "H1CurrentAccessPredecisionInputSetV1", None)
    require = getattr(core_v1, "require_h1_current_access_predecision_input_set_v1", None)
    if expected_type is None or type(value) is not expected_type or not callable(require):
        _fail("predecision input set has a foreign authority type")
    retained = require(value)
    if retained is not value:
        _fail("predecision input set was not retained by its issuer")
    document = value.to_document()
    if type(document) is not dict:
        _fail("predecision input set document is malformed")
    input_set_id = _cid(
        document.get("h1_current_access_predecision_input_set_id"),
        "predecision input set",
    )
    context = replay["context"]
    expected_bindings = {
        "h1_current_access_predecision_context_id": replay["context_id"],
        "h1_current_access_execution_profile_id": context[
            "h1_current_access_execution_profile_id"
        ],
        "h1_current_access_fresh_exec_runtime_profile_id": _PROFILE.profile_id,
        "h1_current_access_fresh_exec_source_manifest_id": _SOURCE_MANIFEST.manifest_id,
        "h1_current_access_fresh_exec_runtime_manifest_id": runtime_manifest_id,
    }
    if any(document.get(name) != expected for name, expected in expected_bindings.items()):
        _fail("predecision input set crossed its context or prelaunch manifests")
    if document.get("sealed_inputs") != _sealed_input_rows(raw_by_role, replay):
        _fail("predecision input set did not bind every exact sealed input")
    return input_set_id, document


def _child_result_payload(
    replay: Mapping[str, Any],
    *,
    input_rows: list[dict[str, Any]],
    source_manifest_id: str,
    runtime_manifest_id: str,
    predecision_input_set_id: str,
) -> dict[str, Any]:
    context = replay["context"]
    return {
        "schema": "acfqp.construction_k7_h1_current_access_child_result.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "h1_current_access_predecision_context_id": replay["context_id"],
        "h1_current_access_execution_profile_id": context[
            "h1_current_access_execution_profile_id"
        ],
        "h1_current_access_fresh_exec_source_manifest_id": source_manifest_id,
        "h1_current_access_fresh_exec_runtime_manifest_id": runtime_manifest_id,
        "h1_current_access_predecision_input_set_id": predecision_input_set_id,
        "h1_current_source_fixture_id": replay["source_id"],
        "h1_durable_proof_match_attestation_id": replay["proof_id"],
        "h1_direct_fallback_two_role_recipe_id": replay["recipe_id"],
        "production_current_identity_candidate_id": replay["candidate_id"],
        "candidate_verification_id": replay["candidate_verification_id"],
        "exact_infeasibility_identity_id": context[
            "exact_infeasibility_identity_id"
        ],
        **{name: context[name] for name in _IDENTITY_COORDINATES},
        "logical_occurrence_id": context["logical_occurrence_id"],
        "route_attempt_id": context["route_attempt_id"],
        "session_nonce": context["session_nonce"],
        "sealed_inputs": input_rows,
        "exact_contract_2_0_52_structural_replay": True,
        "project_package_imported": False,
        "kernel_or_query_object_constructed": False,
        "proof_verifier_or_planner_invoked": False,
        "caller_or_child_zero_counts_accepted": False,
        "production_current_access_authority_issued": False,
    }


# The child source is standalone on purpose.  It repeats the small structural
# replay instead of importing this module or any other project source.
_CHILD_SOURCE = r'''
import fcntl
import hashlib
import json
import os
import socket
import stat
import struct
import sys

ROLES = ("PREDECISION_CONTEXT","CURRENT_SOURCE_FIXTURE","PROOF_MATCH_ATTESTATION","H1_TWO_ROLE_RECIPE","CURRENT_IDENTITY_CANDIDATE","CANDIDATE_VERIFICATION")
DOMAINS = {
 "context":"acfqp:construction-k7-h1-current-access-predecision-context:v1",
 "build":"acfqp:construction-k7-h1-current-build-kernel-attestation:v1",
 "query":"acfqp:construction-k7-h1-current-query-attestation:v1",
 "source":"acfqp:construction-k7-h1-current-source-fixture:v1",
 "proof":"acfqp:construction-k7-h1-durable-proof-match-attestation:v1",
 "recipe":"acfqp:construction-k7-h1-direct-fallback-two-role-recipe:v1",
 "candidate":"acfqp:construction-k7-h1-production-current-identity:v1",
 "candidate_verification":"acfqp:construction-k7-h1-production-current-identity-verification:v1",
 "identity":"acfqp:phase3e-exact-infeasibility-identity:v1",
 "child_result":"acfqp:construction-k7-h1-current-access-child-result:v1",
}
COORDS = ("structural_id","query_id","BuildEpoch_id","kernel_id","threshold_profile_id","reward_profile_id","policy_class_id","complete_search_profile_id")
FORBIDDEN_DECL = {"kind":"FORBIDDEN_API_DECLARATION_NOT_OBSERVED_COUNTERS","forbidden_operations":["DURABLE_PROOF_PRODUCER_OR_VERIFIER","FALLBACK_SOLVER","GROUND_OUTCOME_ENUMERATION","J0_OR_OTHER_PLANNER","KERNEL_STEP"],"caller_supplied_zero_counters_accepted":False}
UNOBSERVED = {"kind":"UNOBSERVED","reason":"OBSERVED_ROUTE_TIME_ACCESS_LOG_PENDING"}

def die(code):
 os._exit(code)
def unique(pairs):
 out={}
 for key,value in pairs:
  if key in out: die(93)
  out[key]=value
 return out
def canonical(value):
 return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
def parse(raw):
 try:
  value=json.loads(raw.decode("utf-8"),object_pairs_hook=unique,parse_constant=lambda value: die(93))
 except BaseException:
  die(93)
 if type(value) is not dict or canonical(value)!=raw: die(93)
 return value
def cid(domain,payload):
 return hashlib.sha256(domain.encode("utf-8")+b"\x00"+canonical(payload)).hexdigest()
def embedded(document,field,domain,excluded=()):
 value=document.get(field)
 if type(value) is not str or len(value)!=64: die(94)
 payload=dict(document); payload.pop(field,None)
 for name in excluded: payload.pop(name,None)
 if cid(domain,payload)!=value: die(94)
 return value
def read_fd(fd):
 status=os.fstat(fd)
 seals=fcntl.fcntl(fd,1034)
 if not stat.S_ISREG(status.st_mode) or status.st_size<=0 or status.st_size>16777216 or seals & 15 != 15: die(91)
 chunks=[]; offset=0
 while offset<status.st_size:
  chunk=os.pread(fd,min(1048576,status.st_size-offset),offset)
  if not chunk: die(91)
  chunks.append(chunk); offset+=len(chunk)
 after=os.fstat(fd)
 if (status.st_dev,status.st_ino,status.st_size)!=(after.st_dev,after.st_ino,after.st_size) or fcntl.fcntl(fd,1034)!=seals: die(91)
 return b"".join(chunks)
def crosswalk(identity,projection):
 names={"structural_id":"structural_id","query_id":"query_id","BuildEpoch_id":"BuildEpoch_id","kernel_id":"kernel_id","threshold_profile_id":"threshold_profile_id"}
 rows=[]
 for name in COORDS:
  other=names.get(name); value=None if other is None else projection[other]
  rows.append({"coordinate":name,"current_value":identity[name],"proof_match_value":identity[name],"recipe_value":value,"recipe_coordinate_applicable":value is not None})
 return rows

try:
 if len(sys.argv)!=5 or not (sys.flags.isolated==1 and sys.flags.no_site==1 and sys.flags.dont_write_bytecode==1): die(80)
 if sorted(os.environ)!=["ACFQP_H1_CURRENT_ACCESS_CHANNEL_FD","ACFQP_H1_CURRENT_ACCESS_INPUT_FDS","LANG","LC_ALL","TZ"]: die(80)
 if os.environ["LANG"]!="C" or os.environ["LC_ALL"]!="C" or os.environ["TZ"]!="UTC": die(80)
 channel_fd=int(os.environ["ACFQP_H1_CURRENT_ACCESS_CHANNEL_FD"])
 fds=tuple(int(item) for item in os.environ["ACFQP_H1_CURRENT_ACCESS_INPUT_FDS"].split(","))
 if len(fds)!=6 or len(set((channel_fd,*fds)))!=7 or min(channel_fd,*fds)<3: die(81)
 expected_source=sys.argv[1]; source_manifest_id=sys.argv[2]; runtime_manifest_id=sys.argv[3]; input_set_id=sys.argv[4]
 if any(type(value) is not str or len(value)!=64 or any(character not in "0123456789abcdef" for character in value) for value in (expected_source,source_manifest_id,runtime_manifest_id,input_set_id)): die(82)
 visible=[]
 for name in os.listdir("/proc/self/fd"):
  try:
   descriptor=int(name); os.fstat(descriptor); visible.append(descriptor)
  except (OSError,ValueError):
   pass
 if sorted(visible)!=sorted((0,1,2,channel_fd,*fds)): die(83)
 if any(type(path) is not str or not path.startswith("/usr/lib/") or path==os.getcwd() or path.startswith(os.getcwd()+"/") for path in sys.path): die(84)
 if any(name=="acfqp" or name.startswith("acfqp.") for name in sys.modules): die(84)
 channel=socket.socket(fileno=channel_fd)
 ready=canonical({"kind":"READY","pid":os.getpid(),"fd_numbers":sorted((0,1,2,channel_fd,*fds)),"isolated":True,"no_site":True,"dont_write_bytecode":True,"project_modules_loaded":False,"cwd":os.getcwd(),"sys_path":list(sys.path)})
 channel.send(ready)
 go=channel.recv(4096)
 if go!=b'{"kind":"GO"}': die(85)
 raw_by_role={role:read_fd(fd) for role,fd in zip(ROLES,fds)}
 docs={role:parse(raw_by_role[role]) for role in ROLES}
 context=docs["PREDECISION_CONTEXT"]
 context_id=embedded(context,"h1_current_access_predecision_context_id",DOMAINS["context"])
 source=docs["CURRENT_SOURCE_FIXTURE"]; build=source["build_kernel_attestation"]; query=source["query_attestation"]
 build_id=embedded(build,"build_kernel_attestation_id",DOMAINS["build"]); query_id=embedded(query,"query_attestation_id",DOMAINS["query"])
 source_id=embedded(source,"current_source_fixture_id",DOMAINS["source"],("build_kernel_attestation","query_attestation"))
 proof=docs["PROOF_MATCH_ATTESTATION"]; proof_id=embedded(proof,"proof_match_attestation_id",DOMAINS["proof"])
 recipe=docs["H1_TWO_ROLE_RECIPE"]; recipe_id=embedded(recipe,"h1_direct_fallback_two_role_recipe_id",DOMAINS["recipe"]); projection=recipe["legacy_h1_preexecution_projection"]
 identity_payload={"schema":"acfqp.phase3e_exact_infeasibility_identity.v1","schema_version":"1.0.0"}
 for name in COORDS: identity_payload[name]=context[name]
 identity=dict(identity_payload); identity["exact_infeasibility_identity_id"]=cid(DOMAINS["identity"],identity_payload)
 if context["exact_infeasibility_identity_id"]!=identity["exact_infeasibility_identity_id"] or source["identity"]!=identity or context["h1_current_source_fixture_id"]!=source_id or context["h1_durable_proof_match_attestation_id"]!=proof_id or source["build_kernel_attestation_id"]!=build_id or source["query_attestation_id"]!=query_id or proof["current_source_fixture_id"]!=source_id or proof["h1_direct_fallback_two_role_recipe_id"]!=recipe_id or proof["exact_infeasibility_identity_id"]!=identity["exact_infeasibility_identity_id"] or projection["exact_infeasibility_identity_id"]!=identity["exact_infeasibility_identity_id"]: die(95)
 for name in ("structural_id","query_id","BuildEpoch_id","kernel_id","threshold_profile_id"):
  if projection[name]!=identity[name]: die(95)
 if projection["selected_plan_id"]!=proof["selected_plan_id"] or projection["logical_occurrence_id"]!=context["logical_occurrence_id"] or projection["route_attempt_id"]!=context["route_attempt_id"]: die(95)
 candidate_payload={"schema":"acfqp.construction_k7_h1_production_current_identity_candidate.v1","schema_version":"1.0.0","proposed_contract_version":"2.0.52","profile_key":"construction_k7_h1_production_current_identity_v1","current_source_fixture_id":source_id,"build_kernel_attestation_id":build_id,"query_attestation_id":query_id,"proof_match_attestation_id":proof_id,"proof_plan_binding_id":proof["plan_binding"]["cache_consumption_id"],"h1_direct_fallback_two_role_recipe_id":recipe_id,"preregistered_recipe_chain":proof["preregistered_recipe_chain"],"identity":identity,"exact_identity_crosswalk":crosswalk(identity,projection),"source_archive_id":source["source_archive_id"],"source_archive_sha256":source["source_archive_sha256"],"source_archive_byte_count":source["source_archive_byte_count"],"durable_proof_id":proof["durable_proof_id"],"durable_proof_verification_id":proof["plan_binding"]["verification_id"],"selected_plan_id":projection["selected_plan_id"],"RouteDecisionContext_id":projection["RouteDecisionContext_id"],"decision_point_id":projection["decision_point_id"],"logical_occurrence_id":projection["logical_occurrence_id"],"route_attempt_id":projection["route_attempt_id"],"route_time_forbidden_api_declaration":FORBIDDEN_DECL,"route_time_call_counts":UNOBSERVED,"route_time_observed_access_log_id":None,"route_time_access_evidence_status":"PENDING_OBSERVED_ACCESS_LOG","current_identity_derived_before_claimant_comparison":True,"claimant_fields_accepted_as_current":False,"legacy_current_identity_used_as_authority":False,"durable_proof_semantics_replayed_at_route_time":False,"source_archive_loaded_execution_claimed":False,"source_archive_is_live_current_issuer_provenance":False,"same_process_unforgeability_claimed":False,"private_module_state_adversary_resistance_claimed":False,"eligible_as_production_consumer_authority":False,"production_consumers_must_reject_candidate":True,"production_current_identity_candidate":True,"production_current_identity_authority":False,"formal_v7_route_authority_present":False,"production_execution_authorized":False,"official_execution_allowed":False,"counter_completeness_gate_status":"COUNTER_COMPLETENESS_GATE_NOT_RUN","workload_economics_gate_status":"WORKLOAD_ECONOMICS_GATE_NOT_RUN","sample_efficiency_gate_status":"SAMPLE_EFFICIENCY_GATE_NOT_RUN","construction_only":True}
 candidate_id=cid(DOMAINS["candidate"],candidate_payload); expected_candidate=dict(candidate_payload); expected_candidate["production_current_identity_candidate_id"]=candidate_id
 if docs["CURRENT_IDENTITY_CANDIDATE"]!=expected_candidate: die(96)
 candidate_raw=raw_by_role["CURRENT_IDENTITY_CANDIDATE"]
 verification_payload={"schema":"acfqp.construction_k7_h1_production_current_identity_candidate_verification.v1","schema_version":"1.0.0","proposed_contract_version":"2.0.52","profile_key":"construction_k7_h1_production_current_identity_v1","production_current_identity_candidate_id":candidate_id,"candidate_sha256":hashlib.sha256(candidate_raw).hexdigest(),"candidate_byte_count":len(candidate_raw),"current_source_fixture_id":source_id,"proof_match_attestation_id":proof_id,"h1_direct_fallback_two_role_recipe_id":recipe_id,"structurally_invokes_durable_proof_verifier":False,"structurally_invokes_kernel_or_planner":False,"route_time_forbidden_api_declaration":FORBIDDEN_DECL,"route_time_call_counts":UNOBSERVED,"route_time_observed_access_log_id":None,"route_time_access_evidence_status":"PENDING_OBSERVED_ACCESS_LOG","exact_structural_replay":True,"production_current_identity_candidate_verified":True,"production_current_identity_authority_verified":False,"same_process_unforgeability_verified":False,"eligible_as_production_consumer_authority":False,"production_consumers_must_reject_candidate":True,"production_execution_authorized":False,"construction_only":True}
 candidate_verification_id=cid(DOMAINS["candidate_verification"],verification_payload); expected_verification=dict(verification_payload); expected_verification["verification_id"]=candidate_verification_id
 if docs["CANDIDATE_VERIFICATION"]!=expected_verification: die(97)
 artifact_ids=(context_id,source_id,proof_id,recipe_id,candidate_id,candidate_verification_id)
 input_rows=[{"role":role,"artifact_id":artifact_id,"sha256":hashlib.sha256(raw_by_role[role]).hexdigest(),"byte_count":len(raw_by_role[role])} for role,artifact_id in zip(ROLES,artifact_ids)]
 result={"schema":"acfqp.construction_k7_h1_current_access_child_result.v1","schema_version":"1.0.0","proposed_contract_version":"2.0.57","profile_key":"construction_k7_h1_current_access_fresh_exec_runtime_v1","h1_current_access_predecision_context_id":context_id,"h1_current_access_execution_profile_id":context["h1_current_access_execution_profile_id"],"h1_current_access_fresh_exec_source_manifest_id":source_manifest_id,"h1_current_access_fresh_exec_runtime_manifest_id":runtime_manifest_id,"h1_current_access_predecision_input_set_id":input_set_id,"h1_current_source_fixture_id":source_id,"h1_durable_proof_match_attestation_id":proof_id,"h1_direct_fallback_two_role_recipe_id":recipe_id,"production_current_identity_candidate_id":candidate_id,"candidate_verification_id":candidate_verification_id,"exact_infeasibility_identity_id":context["exact_infeasibility_identity_id"],"logical_occurrence_id":context["logical_occurrence_id"],"route_attempt_id":context["route_attempt_id"],"session_nonce":context["session_nonce"],"sealed_inputs":input_rows,"exact_contract_2_0_52_structural_replay":True,"project_package_imported":False,"kernel_or_query_object_constructed":False,"proof_verifier_or_planner_invoked":False,"caller_or_child_zero_counts_accepted":False,"production_current_access_authority_issued":False}
 for name in COORDS: result[name]=context[name]
 result["h1_current_access_child_result_id"]=cid(DOMAINS["child_result"],result)
 channel.send(canonical(result)); channel.shutdown(socket.SHUT_WR); channel.close(); raise SystemExit(0)
except SystemExit:
 raise
except BaseException:
 die(99)
'''.strip()


_CHILD_SOURCE_BYTES = _CHILD_SOURCE.encode("utf-8")
_CHILD_SOURCE_SHA256 = _sha(_CHILD_SOURCE_BYTES)


def _static_source_closure(source: str) -> tuple[str, ...]:
    if type(source) is not str or not source:
        raise RuntimeError("H1 current-access child source is not exact text")
    try:
        tree = ast.parse(source, filename="h1-current-access-child-v1")
    except SyntaxError as error:  # pragma: no cover - import invariant
        raise RuntimeError("H1 current-access child source does not compile") from error
    allowed_imports = {
        "fcntl",
        "hashlib",
        "json",
        "os",
        "socket",
        "stat",
        "struct",
        "sys",
    }
    observed: list[str] = []
    banned_calls = {
        "__import__",
        "compile",
        "eval",
        "exec",
        "open",
    }
    banned_attributes = {
        "dlopen",
        "execv",
        "execve",
        "execveat",
        "fork",
        "popen",
        "posix_spawn",
        "spawn",
        "system",
    }
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name not in allowed_imports:
                    raise RuntimeError(
                        "H1 current-access child imports a forbidden module"
                    )
                observed.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            raise RuntimeError("H1 current-access child uses import-from")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in banned_calls:
                raise RuntimeError("H1 current-access child uses dynamic code or open")
            if (
                isinstance(node.func, ast.Attribute)
                and node.func.attr in banned_attributes
            ):
                raise RuntimeError("H1 current-access child uses a forbidden launcher")
    if tuple(observed) != tuple(sorted(allowed_imports)):
        raise RuntimeError("H1 current-access child import closure changed")
    return tuple(observed)


_CHILD_SOURCE_AST_SHA256 = hashlib.sha256(
    ast.dump(
        ast.parse(_CHILD_SOURCE, filename="h1-current-access-child-v1"),
        annotate_fields=True,
        include_attributes=True,
    ).encode("utf-8")
).hexdigest()
_STATIC_IMPORTS = _static_source_closure(_CHILD_SOURCE)


@dataclass(frozen=True, slots=True)
class H1CurrentAccessFreshExecSourceManifestV1:
    _issuer: InitVar[object]
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SOURCE_MANIFEST_ISSUER:
            _fail("fresh-exec source manifest is issuer-owned")
        object.__setattr__(
            self,
            "_manifest_id",
            content_id(
                CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_access_fresh_exec_source_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_sha256": _CHILD_SOURCE_SHA256,
            "full_ast_sha256": _CHILD_SOURCE_AST_SHA256,
            "source_byte_count": len(_CHILD_SOURCE_BYTES),
            "static_imports": list(_STATIC_IMPORTS),
            "project_imports": [],
            "dynamic_import_or_code_calls": 0,
            "full_ast_exact_match_required_at_prelaunch": True,
            "kernel_query_proof_planner_fallback_modules_present": False,
            "exact_contract_2_0_52_structural_replay_only": True,
        }

    @property
    def manifest_id(self) -> str:
        if content_id(
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN,
            self._payload(),
        ) != self._manifest_id:
            _fail("fresh-exec source manifest changed")
        return self._manifest_id

    @property
    def h1_current_access_fresh_exec_source_manifest_id(self) -> str:
        return self.manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_fresh_exec_source_manifest_id": self.manifest_id,
        }


_SOURCE_MANIFEST = H1CurrentAccessFreshExecSourceManifestV1(
    _SOURCE_MANIFEST_ISSUER
)
_retain_static(_SOURCE_MANIFEST, canonical_json_bytes(_SOURCE_MANIFEST.to_document()))


@dataclass(frozen=True, slots=True)
class H1CurrentAccessFreshExecRuntimeProfileV1:
    _issuer: InitVar[object]
    _profile_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROFILE_ISSUER:
            _fail("fresh-exec runtime profile is issuer-owned")
        object.__setattr__(
            self,
            "_profile_id",
            content_id(
                CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_access_fresh_exec_runtime_profile.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "source_manifest_id": _SOURCE_MANIFEST.manifest_id,
            "python_executable": str(PYTHON_EXECUTABLE),
            "python_flags": ["-I", "-S", "-B", "-c"],
            "sealed_input_roles": list(INPUT_ROLES),
            "forbidden_operations": list(FORBIDDEN_OPERATIONS),
            "required_transport": "AF_UNIX_SOCK_SEQPACKET_SCM_CREDENTIALS",
            "pidfd_open_wait_and_pidfd_reap_required": True,
            "exact_child_fd_set_required": True,
            "ambient_repository_or_cwd_import_allowed": False,
            "process_timeout_seconds": PROCESS_TIMEOUT_SECONDS,
            "max_input_bytes": MAX_INPUT_BYTES,
            "max_packet_bytes": MAX_PACKET_BYTES,
            "formal_counter_record_authority": False,
            "production_current_access_authority": False,
        }

    @property
    def profile_id(self) -> str:
        if content_id(
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN,
            self._payload(),
        ) != self._profile_id:
            _fail("fresh-exec runtime profile changed")
        return self._profile_id

    @property
    def h1_current_access_fresh_exec_runtime_profile_id(self) -> str:
        return self.profile_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_fresh_exec_runtime_profile_id": self.profile_id,
        }


_PROFILE = H1CurrentAccessFreshExecRuntimeProfileV1(_PROFILE_ISSUER)
_retain_static(_PROFILE, canonical_json_bytes(_PROFILE.to_document()))


def official_h1_current_access_fresh_exec_runtime_profile_v1(
) -> H1CurrentAccessFreshExecRuntimeProfileV1:
    return _PROFILE


def official_h1_current_access_fresh_exec_source_manifest_v1(
) -> H1CurrentAccessFreshExecSourceManifestV1:
    return _SOURCE_MANIFEST


def require_h1_current_access_fresh_exec_runtime_profile_v1(
    value: Any,
) -> H1CurrentAccessFreshExecRuntimeProfileV1:
    return _require_static(value, H1CurrentAccessFreshExecRuntimeProfileV1, "runtime profile")


def require_h1_current_access_fresh_exec_source_manifest_v1(
    value: Any,
) -> H1CurrentAccessFreshExecSourceManifestV1:
    return _require_static(value, H1CurrentAccessFreshExecSourceManifestV1, "source manifest")


class H1CurrentAccessRuntimeUnavailableReasonV1(str, Enum):
    NOT_LINUX = "NOT_LINUX"
    PROCFS_UNAVAILABLE = "PROCFS_UNAVAILABLE"
    MEMFD_SEALS_UNAVAILABLE = "MEMFD_SEALS_UNAVAILABLE"
    PIDFD_UNAVAILABLE = "PIDFD_UNAVAILABLE"
    PIDFD_WAIT_UNAVAILABLE = "PIDFD_WAIT_UNAVAILABLE"
    PIDFD_SIGNAL_UNAVAILABLE = "PIDFD_SIGNAL_UNAVAILABLE"
    SCM_CREDENTIALS_UNAVAILABLE = "SCM_CREDENTIALS_UNAVAILABLE"
    PYTHON_EXECUTABLE_UNAVAILABLE = "PYTHON_EXECUTABLE_UNAVAILABLE"


@dataclass(frozen=True, slots=True)
class H1CurrentAccessRuntimeUnavailableV1:
    _issuer: InitVar[object]
    reason: H1CurrentAccessRuntimeUnavailableReasonV1
    observed_prerequisites: Mapping[str, bool]
    _unavailable_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _UNAVAILABLE_ISSUER or type(self.observed_prerequisites) is not dict:
            _fail("runtime-unavailable result is issuer-owned")
        object.__setattr__(
            self,
            "_unavailable_id",
            content_id(
                CONSTRUCTION_K7_H1_CURRENT_ACCESS_RUNTIME_UNAVAILABLE_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_access_runtime_unavailable.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_current_access_fresh_exec_runtime_profile_id": _PROFILE.profile_id,
            "reason": self.reason.value,
            "observed_prerequisites": dict(self.observed_prerequisites),
            "process_launches": 0,
            "observed_runtime_facts_issued": False,
            "production_current_access_evidence_issued": False,
        }

    @property
    def unavailable_id(self) -> str:
        return self._unavailable_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_runtime_unavailable_id": self.unavailable_id,
        }


def _prerequisites() -> tuple[
    dict[str, bool], H1CurrentAccessRuntimeUnavailableReasonV1 | None
]:
    observed = {
        "linux": os.name == "posix" and Path("/proc/self/fd").is_dir(),
        "procfs": Path("/proc/self/fd").is_dir()
        and Path("/proc/self/task").is_dir(),
        "memfd_and_seals": callable(getattr(os, "memfd_create", None))
        and hasattr(fcntl, "F_ADD_SEALS")
        and hasattr(fcntl, "F_GET_SEALS"),
        "pidfd_open": callable(getattr(os, "pidfd_open", None)),
        "pidfd_wait": hasattr(os, "P_PIDFD") and callable(getattr(os, "waitid", None)),
        "pidfd_signal": callable(getattr(signal, "pidfd_send_signal", None)),
        "scm_credentials": all(
            hasattr(socket, name) for name in ("SO_PASSCRED", "SCM_CREDENTIALS")
        ),
        "python_executable": PYTHON_EXECUTABLE.is_file()
        and os.access(PYTHON_EXECUTABLE, os.X_OK),
    }
    checks = (
        ("linux", H1CurrentAccessRuntimeUnavailableReasonV1.NOT_LINUX),
        ("procfs", H1CurrentAccessRuntimeUnavailableReasonV1.PROCFS_UNAVAILABLE),
        (
            "memfd_and_seals",
            H1CurrentAccessRuntimeUnavailableReasonV1.MEMFD_SEALS_UNAVAILABLE,
        ),
        ("pidfd_open", H1CurrentAccessRuntimeUnavailableReasonV1.PIDFD_UNAVAILABLE),
        (
            "pidfd_wait",
            H1CurrentAccessRuntimeUnavailableReasonV1.PIDFD_WAIT_UNAVAILABLE,
        ),
        (
            "pidfd_signal",
            H1CurrentAccessRuntimeUnavailableReasonV1.PIDFD_SIGNAL_UNAVAILABLE,
        ),
        (
            "scm_credentials",
            H1CurrentAccessRuntimeUnavailableReasonV1.SCM_CREDENTIALS_UNAVAILABLE,
        ),
        (
            "python_executable",
            H1CurrentAccessRuntimeUnavailableReasonV1.PYTHON_EXECUTABLE_UNAVAILABLE,
        ),
    )
    return observed, next((reason for name, reason in checks if not observed[name]), None)


def _read_regular(path: Path, cap: int, label: str) -> bytes:
    try:
        before = path.stat()
        raw = path.read_bytes()
        after = path.stat()
    except OSError as error:
        raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(
            f"{label} cannot be read"
        ) from error
    if (
        not stat.S_ISREG(before.st_mode)
        or not 0 < len(raw) <= cap
        or (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
        != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    ):
        _fail(f"{label} changed or exceeded its cap")
    return raw


@dataclass(frozen=True, slots=True)
class H1CurrentAccessFreshExecRuntimeManifestV1:
    _issuer: InitVar[object]
    executable_sha256: str
    executable_byte_count: int
    _manifest_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _RUNTIME_MANIFEST_ISSUER:
            _fail("fresh-exec runtime manifest is issuer-owned")
        _cid(self.executable_sha256, "executable digest")
        if type(self.executable_byte_count) is not int or self.executable_byte_count <= 0:
            _fail("fresh-exec executable extent is invalid")
        object.__setattr__(
            self,
            "_manifest_id",
            content_id(
                CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_h1_current_access_fresh_exec_runtime_manifest.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "python_executable": str(PYTHON_EXECUTABLE),
            "executable_sha256": self.executable_sha256,
            "executable_byte_count": self.executable_byte_count,
            "python_flags": ["-I", "-S", "-B", "-c"],
            "pidfd_and_scm_credentials_required": True,
            "cgroup_or_route_execution_authority_claimed": False,
        }

    @property
    def manifest_id(self) -> str:
        if content_id(
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN,
            self._payload(),
        ) != self._manifest_id:
            _fail("fresh-exec runtime manifest changed")
        return self._manifest_id

    @property
    def h1_current_access_fresh_exec_runtime_manifest_id(self) -> str:
        return self.manifest_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_fresh_exec_runtime_manifest_id": self.manifest_id,
        }


_RUNTIME_MANIFEST: H1CurrentAccessFreshExecRuntimeManifestV1 | None = None
_RUNTIME_MANIFEST_LOCK = threading.RLock()


def official_h1_current_access_fresh_exec_runtime_manifest_v1(
) -> H1CurrentAccessFreshExecRuntimeManifestV1:
    """Freeze the exact interpreter bytes before any semantic context is issued."""

    global _RUNTIME_MANIFEST
    with _RUNTIME_MANIFEST_LOCK:
        if _RUNTIME_MANIFEST is None:
            executable_raw = _read_regular(
                PYTHON_EXECUTABLE,
                sealed_runtime_v1.MAX_EXECUTABLE_BYTES,
                "fresh-exec interpreter",
            )
            value = H1CurrentAccessFreshExecRuntimeManifestV1(
                _RUNTIME_MANIFEST_ISSUER,
                _sha(executable_raw),
                len(executable_raw),
            )
            _retain_static(value, canonical_json_bytes(value.to_document()))
            _RUNTIME_MANIFEST = value
        return _RUNTIME_MANIFEST


def require_h1_current_access_fresh_exec_runtime_manifest_v1(
    value: Any,
) -> H1CurrentAccessFreshExecRuntimeManifestV1:
    return _require_static(value, H1CurrentAccessFreshExecRuntimeManifestV1, "runtime manifest")


def _descriptor_identity(fd: int) -> dict[str, int]:
    status = os.fstat(fd)
    return {
        "device": status.st_dev,
        "inode": status.st_ino,
        "mode": stat.S_IMODE(status.st_mode),
        "uid": status.st_uid,
        "gid": status.st_gid,
        "size": status.st_size,
    }


def _proc_start_ticks(pid: int) -> int:
    raw = Path(f"/proc/{pid}/stat").read_text(encoding="ascii")
    closing = raw.rfind(")")
    if closing < 0:
        _fail("child proc stat is malformed")
    fields = raw[closing + 2 :].split()
    value = int(fields[19])
    if value <= 0:
        _fail("child proc start time is invalid")
    return value


def _proc_fd_rows(pid: int) -> list[dict[str, Any]]:
    root = Path(f"/proc/{pid}/fd")
    rows: list[dict[str, Any]] = []
    for path in sorted(root.iterdir(), key=lambda item: int(item.name)):
        fd = int(path.name)
        status = path.stat()
        rows.append(
            {
                "fd": fd,
                "device": status.st_dev,
                "inode": status.st_ino,
                "mode": stat.S_IFMT(status.st_mode),
                "target": os.readlink(path),
            }
        )
    return rows


def _recv_credential_packet(
    endpoint: socket.socket,
    *,
    deadline: float,
    expected_pid: int,
    allow_eof: bool = False,
) -> tuple[bytes, dict[str, int] | None]:
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        _fail("fresh-exec child exceeded its deadline")
    readable, _, _ = select.select([endpoint], [], [], remaining)
    if not readable:
        _fail("fresh-exec child exceeded its deadline")
    raw, ancillary, flags, _address = endpoint.recvmsg(
        MAX_PACKET_BYTES + 1,
        socket.CMSG_SPACE(struct.calcsize("3i")),
    )
    if not raw:
        if allow_eof:
            return b"", None
        _fail("fresh-exec child closed before its required packet")
    if len(raw) > MAX_PACKET_BYTES or flags & (socket.MSG_TRUNC | socket.MSG_CTRUNC):
        _fail("fresh-exec child packet is truncated or over cap")
    credentials = [
        struct.unpack("3i", data[: struct.calcsize("3i")])
        for level, kind, data in ancillary
        if level == socket.SOL_SOCKET and kind == socket.SCM_CREDENTIALS
    ]
    if len(credentials) != 1 or credentials[0][0] != expected_pid:
        _fail("fresh-exec child packet lacks exact kernel credentials")
    pid, uid, gid = credentials[0]
    return raw, {"pid": pid, "uid": uid, "gid": gid}


def _kill_and_reap(process: subprocess.Popen[bytes], pidfd: int | None) -> None:
    if process.returncode is not None:
        return
    try:
        if pidfd is not None:
            signal.pidfd_send_signal(pidfd, signal.SIGKILL)
        else:
            process.kill()
    except (OSError, ProcessLookupError):
        pass
    try:
        process.wait(timeout=5)
    except (OSError, subprocess.SubprocessError):
        pass


def _child_instance_id(
    *, pid: int, start_ticks: int, runtime_manifest_id: str, session_nonce: str
) -> str:
    payload = canonical_json_bytes(
        {
            "pid": pid,
            "start_ticks": start_ticks,
            "runtime_manifest_id": runtime_manifest_id,
            "session_nonce": session_nonce,
        }
    )
    return hashlib.sha256(
        b"acfqp:construction-k7-h1-current-access-child-instance:v1\x00" + payload
    ).hexdigest()


@dataclass(frozen=True, slots=True)
class H1CurrentAccessObservedRuntimeFactsV1:
    _issuer: InitVar[object]
    document: Mapping[str, Any] = field(repr=False)
    _facts_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _FACTS_ISSUER or type(self.document) is not dict:
            _fail("observed runtime facts are broker-issued")
        payload = dict(self.document)
        identifier = _cid(
            payload.pop("h1_current_access_observed_runtime_facts_id", None),
            "observed runtime facts",
        )
        if content_id(
            CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
            payload,
        ) != identifier:
            _fail("observed runtime facts content identity is invalid")
        object.__setattr__(self, "_facts_id", identifier)

    @property
    def facts_id(self) -> str:
        retained = _LIVE_FACTS.get(self._facts_id)
        raw = canonical_json_bytes(dict(self.document))
        if retained is None or retained[0] is not self or not hmac.compare_digest(retained[1], raw):
            _fail("observed runtime facts lost broker retention")
        return self._facts_id

    def to_document(self) -> dict[str, Any]:
        _ = self.facts_id
        return dict(self.document)

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def __getattr__(self, name: str) -> Any:
        aliases = {
            "predecision_context_id": "h1_current_access_predecision_context_id",
            "execution_profile_id": "h1_current_access_execution_profile_id",
            "source_manifest_id": "h1_current_access_fresh_exec_source_manifest_id",
            "runtime_manifest_id": "h1_current_access_fresh_exec_runtime_manifest_id",
            "build_epoch_id": "BuildEpoch_id",
        }
        key = aliases.get(name, name)
        if key in self.document:
            return self.document[key]
        raise AttributeError(name)


_LIVE_FACTS: dict[str, tuple[H1CurrentAccessObservedRuntimeFactsV1, bytes]] = {}


@dataclass(frozen=True, slots=True)
class H1CurrentAccessObservedRuntimeFactsVerificationV1:
    _issuer: InitVar[object]
    facts: H1CurrentAccessObservedRuntimeFactsV1 = field(repr=False)
    input_bytes: tuple[bytes, ...] = field(repr=False)
    predecision_input_set: Any = field(repr=False)
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _VERIFICATION_ISSUER
            or type(self.facts) is not H1CurrentAccessObservedRuntimeFactsV1
            or type(self.input_bytes) is not tuple
            or len(self.input_bytes) != len(INPUT_ROLES)
        ):
            _fail("observed runtime verification is verifier-issued")
        _verify_facts_semantics(
            self.facts, self.input_bytes, self.predecision_input_set
        )
        object.__setattr__(
            self,
            "_verification_id",
            content_id(
                CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_VERIFICATION_V1_DOMAIN,
                self._payload(),
            ),
        )

    def _payload(self) -> dict[str, Any]:
        document = self.facts.to_document()
        return {
            "schema": "acfqp.construction_k7_h1_current_access_observed_runtime_facts_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "h1_current_access_observed_runtime_facts_id": self.facts.facts_id,
            "h1_current_access_fresh_exec_runtime_profile_id": _PROFILE.profile_id,
            "h1_current_access_fresh_exec_source_manifest_id": document[
                "h1_current_access_fresh_exec_source_manifest_id"
            ],
            "h1_current_access_fresh_exec_runtime_manifest_id": document[
                "h1_current_access_fresh_exec_runtime_manifest_id"
            ],
            "h1_current_access_predecision_input_set_id": document[
                "h1_current_access_predecision_input_set_id"
            ],
            "h1_current_access_predecision_context_id": document[
                "h1_current_access_predecision_context_id"
            ],
            "h1_current_access_execution_profile_id": document[
                "h1_current_access_execution_profile_id"
            ],
            "h1_current_source_fixture_id": document[
                "h1_current_source_fixture_id"
            ],
            "h1_durable_proof_match_attestation_id": document[
                "h1_durable_proof_match_attestation_id"
            ],
            "h1_direct_fallback_two_role_recipe_id": document[
                "h1_direct_fallback_two_role_recipe_id"
            ],
            "h1_production_current_identity_candidate_id": document[
                "h1_production_current_identity_candidate_id"
            ],
            "h1_production_current_identity_candidate_verification_id": document[
                "h1_production_current_identity_candidate_verification_id"
            ],
            "exact_infeasibility_identity_id": document[
                "exact_infeasibility_identity_id"
            ],
            **{name: document[name] for name in _IDENTITY_COORDINATES},
            "logical_occurrence_id": document["logical_occurrence_id"],
            "route_attempt_id": document["route_attempt_id"],
            "session_nonce": document["session_nonce"],
            "child_instance_id": document["child_instance_id"],
            "verification_status": VERIFICATION_STATUS,
            "semantic_bytes_replayed": True,
            "live_broker_facts_retained": True,
            "production_current_access_authority_issued": False,
        }

    @property
    def verification_id(self) -> str:
        retained = _LIVE_VERIFICATIONS.get(self._verification_id)
        if retained is None or retained is not self:
            _fail("observed runtime verification lost retention")
        _verify_facts_semantics(
            self.facts, self.input_bytes, self.predecision_input_set
        )
        return self._verification_id

    @property
    def verification_status(self) -> str:
        return VERIFICATION_STATUS

    @property
    def facts_id(self) -> str:
        return self.facts.facts_id

    @property
    def h1_current_access_observed_runtime_facts_id(self) -> str:
        return self.facts_id

    @property
    def h1_current_access_observed_runtime_facts_verification_id(self) -> str:
        return self.verification_id

    @property
    def predecision_context_id(self) -> str:
        return self.facts.predecision_context_id

    @property
    def source_manifest_id(self) -> str:
        return self.facts.source_manifest_id

    @property
    def h1_current_access_fresh_exec_source_manifest_id(self) -> str:
        return self.source_manifest_id

    @property
    def runtime_manifest_id(self) -> str:
        return self.facts.runtime_manifest_id

    @property
    def h1_current_access_fresh_exec_runtime_manifest_id(self) -> str:
        return self.runtime_manifest_id

    @property
    def h1_current_access_predecision_input_set_id(self) -> str:
        return self.facts.h1_current_access_predecision_input_set_id

    def __getattr__(self, name: str) -> Any:
        return getattr(self.facts, name)

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_current_access_observed_runtime_facts_verification_id": (
                self.verification_id
            ),
        }


_LIVE_VERIFICATIONS: dict[
    str, H1CurrentAccessObservedRuntimeFactsVerificationV1
] = {}


def _verify_facts_semantics(
    facts: H1CurrentAccessObservedRuntimeFactsV1,
    input_bytes: tuple[bytes, ...],
    predecision_input_set: Any,
) -> None:
    document = facts.to_document()
    raw_by_role = dict(zip(INPUT_ROLES, input_bytes))
    replay = _structural_replay(raw_by_role)
    rows = _sealed_input_rows(raw_by_role, replay)
    runtime_manifest = official_h1_current_access_fresh_exec_runtime_manifest_v1()
    input_set_id, _input_set_document = _require_predecision_input_set(
        predecision_input_set,
        raw_by_role=raw_by_role,
        replay=replay,
        runtime_manifest_id=runtime_manifest.manifest_id,
    )
    expected_child_payload = _child_result_payload(
        replay,
        input_rows=rows,
        source_manifest_id=_SOURCE_MANIFEST.manifest_id,
        runtime_manifest_id=document["h1_current_access_fresh_exec_runtime_manifest_id"],
        predecision_input_set_id=input_set_id,
    )
    expected_child_id = content_id(
        CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
        expected_child_payload,
    )
    required_true = (
        "fresh_exec_observed",
        "distinct_child_process_observed",
        "exact_executable_observed",
        "exact_source_argv_observed",
        "exact_sealed_input_fd_set_observed",
        "scm_credentials_observed",
        "output_eof_observed",
        "zero_exit_observed",
        "pidfd_terminal_observed",
        "pidfd_reap_observed",
        "direct_reap_observed",
        "popen_returncode_synchronized_after_pidfd_reap",
        "ambient_repository_path_absent",
        "capability_closure_complete",
    )
    if (
        document.get("schema")
        != "acfqp.construction_k7_h1_current_access_observed_runtime_facts.v1"
        or document.get("verification_status") != VERIFICATION_STATUS
        or document.get("h1_current_access_fresh_exec_runtime_profile_id")
        != _PROFILE.profile_id
        or document.get("h1_current_access_fresh_exec_source_manifest_id")
        != _SOURCE_MANIFEST.manifest_id
        or document.get("h1_current_access_fresh_exec_runtime_manifest_id")
        != runtime_manifest.manifest_id
        or document.get("h1_current_access_predecision_input_set_id")
        != input_set_id
        or document.get("h1_current_access_predecision_context_id")
        != replay["context_id"]
        or document.get("h1_current_source_fixture_id") != replay["source_id"]
        or document.get("h1_durable_proof_match_attestation_id")
        != replay["proof_id"]
        or document.get("h1_direct_fallback_two_role_recipe_id")
        != replay["recipe_id"]
        or document.get("h1_production_current_identity_candidate_id")
        != replay["candidate_id"]
        or document.get("h1_production_current_identity_candidate_verification_id")
        != replay["candidate_verification_id"]
        or document.get("sealed_inputs") != rows
        or document.get("h1_current_access_child_result_id") != expected_child_id
        or document.get("child_result")
        != {**expected_child_payload, "h1_current_access_child_result_id": expected_child_id}
        or any(document.get(name) is not True for name in required_true)
        or document.get("forbidden_operation_zero_counts")
        != {value: 0 for value in ZERO_CALL_FIELD_BY_OPERATION.values()}
        or document.get("caller_or_child_zero_counts_used") is not False
        or document.get("pidfd_reap_api") != "waitid(P_PIDFD,WEXITED)"
        or document.get("same_process_private_state_adversary_resistance_claimed")
        is not False
        or document.get("concurrent_mutation_during_checkpoint_interval_excluded")
        is not True
        or document.get("production_current_access_authority_issued") is not False
    ):
        _fail("observed runtime facts do not replay against exact inputs")
    context = replay["context"]
    for name in (*_IDENTITY_COORDINATES, "logical_occurrence_id", "route_attempt_id", "session_nonce"):
        if document.get(name) != context[name]:
            _fail("observed runtime facts crossed predecision context")
    if document.get("exact_infeasibility_identity_id") != context[
        "exact_infeasibility_identity_id"
    ]:
        _fail("observed runtime facts crossed exact identity")


def verify_h1_current_access_observed_runtime_facts_bytes_v1(
    raw: bytes,
    *,
    predecision_context_bytes: bytes,
    current_source_fixture_bytes: bytes,
    proof_match_attestation_bytes: bytes,
    h1_two_role_recipe_bytes: bytes,
    current_identity_candidate_bytes: bytes,
    candidate_verification_bytes: bytes,
    predecision_input_set: Any,
) -> H1CurrentAccessObservedRuntimeFactsVerificationV1:
    document = _canonical_document(raw, "observed runtime facts")
    facts_id = _cid(
        document.get("h1_current_access_observed_runtime_facts_id"),
        "observed runtime facts",
    )
    retained = _LIVE_FACTS.get(facts_id)
    if retained is None or not hmac.compare_digest(retained[1], raw):
        _fail("observed runtime facts bytes lack a live broker observation")
    facts = retained[0]
    inputs = (
        predecision_context_bytes,
        current_source_fixture_bytes,
        proof_match_attestation_bytes,
        h1_two_role_recipe_bytes,
        current_identity_candidate_bytes,
        candidate_verification_bytes,
    )
    verification = H1CurrentAccessObservedRuntimeFactsVerificationV1(
        _VERIFICATION_ISSUER,
        facts,
        inputs,
        predecision_input_set,
    )
    _LIVE_VERIFICATIONS[verification._verification_id] = verification  # noqa: SLF001
    return verification


def require_h1_current_access_observed_runtime_facts_verification_v1(
    value: Any,
) -> H1CurrentAccessObservedRuntimeFactsVerificationV1:
    if type(value) is not H1CurrentAccessObservedRuntimeFactsVerificationV1:
        _fail("current-access core requires exact retained runtime verification")
    try:
        _ = value.verification_id
    except ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error:
        raise
    except Exception as error:
        raise ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error(
            "current-access runtime verification is not retained"
        ) from error
    return value


@dataclass(frozen=True, slots=True)
class _FrozenFunctionV1:
    name: str
    value: Any = field(repr=False)
    code: Any = field(repr=False)
    defaults: Any = field(repr=False)
    kwdefaults_rows: tuple[tuple[str, Any], ...] | None = field(repr=False)


@dataclass(frozen=True, slots=True)
class _FrozenExternalV1:
    owner: Any = field(repr=False)
    attribute: str
    value: Any = field(repr=False)


@dataclass(frozen=True, slots=True)
class _FrozenRuntimeClosureV1:
    source_text: str = field(repr=False)
    source_bytes: bytes = field(repr=False)
    source_sha256: str
    source_ast_sha256: str
    static_imports: tuple[str, ...]
    python_executable: Path
    profile: H1CurrentAccessFreshExecRuntimeProfileV1 = field(repr=False)
    source_manifest: H1CurrentAccessFreshExecSourceManifestV1 = field(repr=False)
    functions: tuple[_FrozenFunctionV1, ...] = field(repr=False)
    externals: tuple[_FrozenExternalV1, ...] = field(repr=False)
    global_objects: tuple[tuple[str, Any], ...] = field(repr=False)
    sha256_function: Any = field(repr=False)
    ast_parse_function: Any = field(repr=False)
    ast_dump_function: Any = field(repr=False)


def _freeze_function(name: str) -> _FrozenFunctionV1:
    value = globals()[name]
    kwdefaults = getattr(value, "__kwdefaults__", None)
    return _FrozenFunctionV1(
        name,
        value,
        getattr(value, "__code__", None),
        getattr(value, "__defaults__", None),
        None if kwdefaults is None else tuple(sorted(kwdefaults.items())),
    )


_FROZEN_RUNTIME_CLOSURE = _FrozenRuntimeClosureV1(
    source_text=_CHILD_SOURCE,
    source_bytes=_CHILD_SOURCE_BYTES,
    source_sha256=_CHILD_SOURCE_SHA256,
    source_ast_sha256=_CHILD_SOURCE_AST_SHA256,
    static_imports=_STATIC_IMPORTS,
    python_executable=PYTHON_EXECUTABLE,
    profile=_PROFILE,
    source_manifest=_SOURCE_MANIFEST,
    functions=tuple(
        _freeze_function(name)
        for name in (
            "_canonical_document",
            "_candidate_crosswalk",
            "_child_instance_id",
            "_child_result_payload",
            "_cid",
            "_descriptor_identity",
            "_embedded_id",
            "_fail",
            "_identity_from_context",
            "_kill_and_reap",
            "_prerequisites",
            "_proc_fd_rows",
            "_proc_start_ticks",
            "_read_regular",
            "_recv_credential_packet",
            "_require_static",
            "_require_predecision_input_set",
            "_retain_static",
            "_sealed_input_rows",
            "_sha",
            "_static_source_closure",
            "_structural_replay",
            "_verify_facts_semantics",
            "official_h1_current_access_fresh_exec_runtime_manifest_v1",
            "official_h1_current_access_fresh_exec_runtime_profile_v1",
            "official_h1_current_access_fresh_exec_source_manifest_v1",
            "require_h1_current_access_fresh_exec_runtime_manifest_v1",
            "require_h1_current_access_fresh_exec_runtime_profile_v1",
            "require_h1_current_access_fresh_exec_source_manifest_v1",
            "verify_h1_current_access_observed_runtime_facts_bytes_v1",
        )
    ),
    externals=tuple(
        _FrozenExternalV1(owner, attribute, getattr(owner, attribute, None))
        for owner, attribute in (
            (fcntl, "fcntl"),
            (hashlib, "sha256"),
            (hmac, "compare_digest"),
            (os, "close"),
            (os, "access"),
            (os, "CLD_EXITED"),
            (os, "fstat"),
            (os, "getpid"),
            (os, "memfd_create"),
            (os, "P_PIDFD"),
            (os, "pidfd_open"),
            (os, "readlink"),
            (os, "WEXITED"),
            (os, "WNOWAIT"),
            (os, "waitid"),
            (Path, "cwd"),
            (Path, "is_dir"),
            (Path, "is_file"),
            (Path, "iterdir"),
            (Path, "read_bytes"),
            (Path, "read_text"),
            (Path, "stat"),
            (select, "select"),
            (select, "poll"),
            (signal, "pidfd_send_signal"),
            (signal, "SIGKILL"),
            (socket, "AF_UNIX"),
            (socket, "CMSG_SPACE"),
            (socket, "MSG_CTRUNC"),
            (socket, "MSG_TRUNC"),
            (socket, "SCM_CREDENTIALS"),
            (socket, "SOCK_CLOEXEC"),
            (socket, "SOCK_SEQPACKET"),
            (socket, "SOL_SOCKET"),
            (socket, "SO_PASSCRED"),
            (socket, "socket"),
            (socket.socket, "close"),
            (socket.socket, "recvmsg"),
            (socket.socket, "send"),
            (socket.socket, "setsockopt"),
            (socket.socket, "shutdown"),
            (socket, "socketpair"),
            (stat, "S_IFMT"),
            (stat, "S_IMODE"),
            (stat, "S_ISREG"),
            (subprocess, "Popen"),
            (subprocess, "DEVNULL"),
            (subprocess.Popen, "kill"),
            (subprocess.Popen, "wait"),
            (tempfile, "TemporaryDirectory"),
            (time, "monotonic"),
            (
                sealed_runtime_v1,
                "create_v075_k7_sealed_memfd_from_bytes_v1",
            ),
            (sealed_runtime_v1, "MAX_EXECUTABLE_BYTES"),
        )
    ),
    global_objects=tuple(
        (name, globals()[name])
        for name in (
            "FORBIDDEN_OPERATIONS",
            "INPUT_ROLES",
            "MAX_INPUT_BYTES",
            "MAX_PACKET_BYTES",
            "PROCESS_TIMEOUT_SECONDS",
            "PROFILE_KEY",
            "PROPOSED_CONTRACT_VERSION",
            "PYTHON_EXECUTABLE",
            "SCHEMA_VERSION",
            "VERIFICATION_STATUS",
            "ZERO_CALL_FIELD_BY_OPERATION",
            "_CHILD_SOURCE",
            "_CHILD_SOURCE_BYTES",
            "_CHILD_SOURCE_AST_SHA256",
            "_CHILD_SOURCE_SHA256",
            "_CURRENT_CONTEXT_FIELDS",
            "_DOMAIN_TEXT",
            "_FACTS_ISSUER",
            "_IDENTITY_COORDINATES",
            "_LIVE_FACTS",
            "_LIVE_VERIFICATIONS",
            "_PROFILE",
            "_ROUTE_FORBIDDEN_DECLARATION",
            "_SOURCE_MANIFEST",
            "_STATIC_IMPORTS",
            "_STATIC_RETENTION",
            "_STATIC_RETENTION_LOCK",
            "_UNOBSERVED_CALLS",
            "_UNAVAILABLE_ISSUER",
            "_VERIFICATION_ISSUER",
            "H1CurrentAccessObservedRuntimeFactsV1",
            "H1CurrentAccessObservedRuntimeFactsVerificationV1",
            "H1CurrentAccessRuntimeUnavailableV1",
            "canonical_json_bytes",
            "content_id",
            "fcntl",
            "hashlib",
            "hmac",
            "loads_canonical_json",
            "os",
            "parse_content_id",
            "Path",
            "select",
            "signal",
            "socket",
            "stat",
            "subprocess",
            "tempfile",
            "time",
        )
    ),
    sha256_function=hashlib.sha256,
    ast_parse_function=ast.parse,
    ast_dump_function=ast.dump,
)


def _verify_frozen_runtime_closure_v1(
    frozen: _FrozenRuntimeClosureV1,
    _error_type: Any = ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
    _static_closure: Any = _static_source_closure,
    _closure_type: Any = _FrozenRuntimeClosureV1,
) -> None:
    if type(frozen) is not _closure_type:
        raise _error_type("fresh-exec runtime closure has a foreign type")
    if any(globals().get(name) is not value for name, value in frozen.global_objects):
        raise _error_type(
            "fresh-exec source/profile global object changed after import"
        )
    for row in frozen.functions:
        current = globals().get(row.name)
        current_kwdefaults = getattr(current, "__kwdefaults__", None)
        current_kwdefault_rows = (
            None
            if current_kwdefaults is None
            else tuple(sorted(current_kwdefaults.items()))
        )
        if (
            current is not row.value
            or getattr(current, "__code__", None) is not row.code
            or getattr(current, "__defaults__", None) is not row.defaults
            or current_kwdefault_rows != row.kwdefaults_rows
        ):
            raise _error_type(
                f"fresh-exec helper {row.name} changed after import"
            )
    for row in frozen.externals:
        current = getattr(row.owner, row.attribute, None)
        current_function = getattr(current, "__func__", None)
        frozen_function = getattr(row.value, "__func__", None)
        if current is not row.value and (
            current_function is None
            or frozen_function is None
            or current_function is not frozen_function
        ):
            raise _error_type(
                f"fresh-exec launcher primitive changed after import: "
                f"{getattr(row.owner, '__name__', type(row.owner).__name__)}."
                f"{row.attribute}"
            )
    if (
        frozen.source_text.encode("utf-8") != frozen.source_bytes
        or frozen.sha256_function(frozen.source_bytes).hexdigest()
        != frozen.source_sha256
        or _static_closure(frozen.source_text) != frozen.static_imports
    ):
        raise _error_type(
            "fresh-exec exact source or static capability closure changed"
        )
    full_ast = frozen.ast_dump_function(
        frozen.ast_parse_function(
            frozen.source_text, filename="h1-current-access-child-v1"
        ),
        annotate_fields=True,
        include_attributes=True,
    ).encode("utf-8")
    if frozen.sha256_function(full_ast).hexdigest() != frozen.source_ast_sha256:
        raise _error_type("fresh-exec full child AST changed after import")


def _run_h1_current_access_fresh_exec_runtime_impl_v1(
    *,
    predecision_context_bytes: bytes,
    current_source_fixture_bytes: bytes,
    proof_match_attestation_bytes: bytes,
    h1_two_role_recipe_bytes: bytes,
    current_identity_candidate_bytes: bytes,
    candidate_verification_bytes: bytes,
    predecision_input_set: Any,
    _frozen: _FrozenRuntimeClosureV1,
    _verify_frozen: Any,
    _observed_prerequisites: Mapping[str, bool],
    _prerequisite_blocker: H1CurrentAccessRuntimeUnavailableReasonV1 | None,
) -> H1CurrentAccessRuntimeUnavailableV1 | H1CurrentAccessObservedRuntimeFactsVerificationV1:
    """Execute one exact structural child or return a prelaunch unavailable result."""

    if _prerequisite_blocker is not None:
        return H1CurrentAccessRuntimeUnavailableV1(
            _UNAVAILABLE_ISSUER,
            _prerequisite_blocker,
            dict(_observed_prerequisites),
        )
    _verify_frozen(_frozen)
    require_h1_current_access_fresh_exec_runtime_profile_v1(_frozen.profile)
    require_h1_current_access_fresh_exec_source_manifest_v1(
        _frozen.source_manifest
    )
    inputs = (
        predecision_context_bytes,
        current_source_fixture_bytes,
        proof_match_attestation_bytes,
        h1_two_role_recipe_bytes,
        current_identity_candidate_bytes,
        candidate_verification_bytes,
    )
    raw_by_role = dict(zip(INPUT_ROLES, inputs))
    replay = _structural_replay(raw_by_role)
    context = replay["context"]
    input_rows = _sealed_input_rows(raw_by_role, replay)
    runtime_manifest = official_h1_current_access_fresh_exec_runtime_manifest_v1()
    require_h1_current_access_fresh_exec_runtime_manifest_v1(runtime_manifest)
    expected_prelaunch_bindings = {
        "h1_current_access_fresh_exec_runtime_profile_id": _frozen.profile.profile_id,
        "h1_current_access_fresh_exec_source_manifest_id": _frozen.source_manifest.manifest_id,
        "h1_current_access_fresh_exec_runtime_manifest_id": runtime_manifest.manifest_id,
    }
    if any(context.get(name) != expected for name, expected in expected_prelaunch_bindings.items()):
        _fail("predecision context crossed its frozen fresh-exec manifests")
    input_set_id, _input_set_document = _require_predecision_input_set(
        predecision_input_set,
        raw_by_role=raw_by_role,
        replay=replay,
        runtime_manifest_id=runtime_manifest.manifest_id,
    )
    executable_raw = _read_regular(
        _frozen.python_executable,
        sealed_runtime_v1.MAX_EXECUTABLE_BYTES,
        "fresh-exec interpreter",
    )
    if (
        _sha(executable_raw) != runtime_manifest.executable_sha256
        or len(executable_raw) != runtime_manifest.executable_byte_count
    ):
        _fail("fresh-exec interpreter changed after prelaunch manifest freeze")
    staged_fds: list[int] = []
    parent_endpoint: socket.socket | None = None
    child_endpoint: socket.socket | None = None
    process: subprocess.Popen[bytes] | None = None
    pidfd: int | None = None
    ready_raw = b""
    child_raw = b""
    credentials: list[dict[str, int]] = []
    staged_descriptor_rows: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix="acfqp-h1-current-access-") as sandbox:
        try:
            for index, raw in enumerate(inputs):
                staged_fds.append(
                    sealed_runtime_v1.create_v075_k7_sealed_memfd_from_bytes_v1(
                        raw=raw,
                        name=f"acfqp-h1-current-access-{index}",
                        byte_cap=MAX_INPUT_BYTES,
                    )
                )
            for role, descriptor, row in zip(INPUT_ROLES, staged_fds, input_rows):
                descriptor_identity = _descriptor_identity(descriptor)
                seals = fcntl.fcntl(descriptor, fcntl.F_GET_SEALS)
                required_seals = (
                    fcntl.F_SEAL_SEAL
                    | fcntl.F_SEAL_SHRINK
                    | fcntl.F_SEAL_GROW
                    | fcntl.F_SEAL_WRITE
                )
                if (
                    descriptor_identity["size"] != row["byte_count"]
                    or seals & required_seals != required_seals
                ):
                    _fail("broker-created input descriptor is not exactly sealed")
                staged_descriptor_rows.append(
                    {
                        "role": role,
                        "fd": descriptor,
                        "artifact_id": row["artifact_id"],
                        **descriptor_identity,
                        "seals": seals,
                    }
                )
            parent_endpoint, child_endpoint = socket.socketpair(
                socket.AF_UNIX,
                socket.SOCK_SEQPACKET | socket.SOCK_CLOEXEC,
            )
            parent_endpoint.setsockopt(socket.SOL_SOCKET, socket.SO_PASSCRED, 1)
            child_fd = child_endpoint.fileno()
            environment = {
                "LANG": "C",
                "LC_ALL": "C",
                "TZ": "UTC",
                "ACFQP_H1_CURRENT_ACCESS_CHANNEL_FD": str(child_fd),
                "ACFQP_H1_CURRENT_ACCESS_INPUT_FDS": ",".join(
                    str(value) for value in staged_fds
                ),
            }
            argv = [
                str(_frozen.python_executable),
                "-I",
                "-S",
                "-B",
                "-c",
                _frozen.source_text,
                _frozen.source_sha256,
                _frozen.source_manifest.manifest_id,
                runtime_manifest.manifest_id,
                input_set_id,
            ]
            _verify_frozen(_frozen)
            process = subprocess.Popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                cwd=sandbox,
                env=environment,
                close_fds=True,
                pass_fds=(*staged_fds, child_fd),
                start_new_session=True,
            )
            child_endpoint.close()
            child_endpoint = None
            if process.pid == os.getpid() or process.pid <= 0:
                _fail("fresh-exec verifier is not one distinct child")
            pidfd = os.pidfd_open(process.pid, 0)
            start_ticks = _proc_start_ticks(process.pid)
            deadline = time.monotonic() + PROCESS_TIMEOUT_SECONDS
            ready_raw, credential = _recv_credential_packet(
                parent_endpoint,
                deadline=deadline,
                expected_pid=process.pid,
            )
            if credential is None:  # pragma: no cover - required above
                _fail("fresh-exec READY lacks credentials")
            credentials.append(credential)
            ready = _canonical_document(ready_raw, "fresh-exec READY")
            expected_fds = sorted((0, 1, 2, child_fd, *staged_fds))
            proc_rows = _proc_fd_rows(process.pid)
            proc_fd_numbers = [row["fd"] for row in proc_rows]
            cmdline_raw = Path(f"/proc/{process.pid}/cmdline").read_bytes()
            expected_cmdline = b"\x00".join(
                value.encode("utf-8") for value in argv
            ) + b"\x00"
            observed_executable_raw = _read_regular(
                Path(f"/proc/{process.pid}/exe"),
                sealed_runtime_v1.MAX_EXECUTABLE_BYTES,
                "live child executable",
            )
            observed_cwd = os.readlink(f"/proc/{process.pid}/cwd")
            if (
                ready
                != {
                    "kind": "READY",
                    "pid": process.pid,
                    "fd_numbers": expected_fds,
                    "isolated": True,
                    "no_site": True,
                    "dont_write_bytecode": True,
                    "project_modules_loaded": False,
                    "cwd": sandbox,
                    "sys_path": ready.get("sys_path"),
                }
                or type(ready.get("sys_path")) is not list
                or any(
                    type(path) is not str
                    or not path.startswith("/usr/lib/")
                    or path == sandbox
                    or path.startswith(sandbox + "/")
                    or path == str(Path.cwd())
                    or path.startswith(str(Path.cwd()) + "/")
                    for path in ready["sys_path"]
                )
                or proc_fd_numbers != expected_fds
                or any(
                    next(
                        (
                            row
                            for row in proc_rows
                            if row["fd"] == staged["fd"]
                        ),
                        None,
                    )
                    != {
                        "fd": staged["fd"],
                        "device": staged["device"],
                        "inode": staged["inode"],
                        "mode": stat.S_IFREG,
                        "target": f"/memfd:acfqp-h1-current-access-{index} (deleted)",
                    }
                    for index, staged in enumerate(staged_descriptor_rows)
                )
                or cmdline_raw != expected_cmdline
                or _sha(observed_executable_raw) != runtime_manifest.executable_sha256
                or len(observed_executable_raw) != runtime_manifest.executable_byte_count
                or observed_cwd != sandbox
            ):
                _fail("broker could not verify exact child source/runtime/FD isolation")
            _verify_frozen(_frozen)
            parent_endpoint.send(b'{"kind":"GO"}')
            child_raw, credential = _recv_credential_packet(
                parent_endpoint,
                deadline=deadline,
                expected_pid=process.pid,
            )
            if credential is None:  # pragma: no cover
                _fail("fresh-exec result lacks credentials")
            credentials.append(credential)
            eof_raw, eof_credential = _recv_credential_packet(
                parent_endpoint,
                deadline=deadline,
                expected_pid=process.pid,
                allow_eof=True,
            )
            if eof_raw or eof_credential is not None:
                _fail("fresh-exec child emitted extra protocol bytes")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                _fail("fresh-exec child exceeded its deadline before reap")
            poller = select.poll()
            poller.register(pidfd, select.POLLIN | select.POLLHUP | select.POLLERR)
            if not poller.poll(max(1, int(remaining * 1000))):
                _fail("fresh-exec child pidfd did not become terminal")
            waited = os.waitid(os.P_PIDFD, pidfd, os.WEXITED | os.WNOWAIT)
            if (
                waited.si_pid != process.pid
                or waited.si_code != os.CLD_EXITED
                or waited.si_status != 0
            ):
                _fail("fresh-exec child did not reach zero-exit terminal state")
            reaped = os.waitid(os.P_PIDFD, pidfd, os.WEXITED)
            if (
                reaped.si_pid != process.pid
                or reaped.si_code != os.CLD_EXITED
                or reaped.si_status != 0
            ):
                _fail("fresh-exec child pidfd reap returned nonzero")
            # Popen did not reap by PID.  Synchronize its local lifecycle state
            # only after the kernel confirmed the P_PIDFD reap above.
            process.returncode = 0
            _verify_frozen(_frozen)
            child_document = _canonical_document(child_raw, "fresh-exec child result")
            child_payload = dict(child_document)
            child_result_id = _cid(
                child_payload.pop("h1_current_access_child_result_id", None),
                "fresh-exec child result",
            )
            expected_child_payload = _child_result_payload(
                replay,
                input_rows=input_rows,
                source_manifest_id=_frozen.source_manifest.manifest_id,
                runtime_manifest_id=runtime_manifest.manifest_id,
                predecision_input_set_id=input_set_id,
            )
            if (
                child_document
                != {
                    **expected_child_payload,
                    "h1_current_access_child_result_id": content_id(
                        CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
                        expected_child_payload,
                    ),
                }
                or content_id(
                    CONSTRUCTION_K7_H1_CURRENT_ACCESS_CHILD_RESULT_V1_DOMAIN,
                    child_payload,
                )
                != child_result_id
            ):
                _fail("fresh-exec child result differs from broker replay")
            child_instance = _child_instance_id(
                pid=process.pid,
                start_ticks=start_ticks,
                runtime_manifest_id=runtime_manifest.manifest_id,
                session_nonce=context["session_nonce"],
            )
            raw_work = {
                "process_launches": 1,
                "sealed_inputs_staged": len(inputs),
                "staged_input_bytes": sum(len(value) for value in inputs),
                "broker_input_digest_bytes": sum(len(value) for value in inputs),
                "child_input_read_bytes": sum(len(value) for value in inputs),
                "source_argv_bytes": len(_frozen.source_bytes),
                "interpreter_digest_read_bytes": len(executable_raw),
                "broker_packets_received": 2,
                "broker_packets_sent": 1,
                "scm_credential_observations": 2,
                "pidfd_opens": 1,
                "pidfd_terminal_observations": 1,
                "direct_child_pidfd_reaps": 1,
                "child_result_bytes": len(child_raw),
                "formal_counter_records_issued": 0,
                "formal_work_vectors_issued": 0,
                "formal_comparison_vectors_issued": 0,
            }
            facts_payload = {
                "schema": "acfqp.construction_k7_h1_current_access_observed_runtime_facts.v1",
                "schema_version": SCHEMA_VERSION,
                "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
                "profile_key": PROFILE_KEY,
                "h1_current_access_fresh_exec_runtime_profile_id": _frozen.profile.profile_id,
                "h1_current_access_fresh_exec_source_manifest_id": _frozen.source_manifest.manifest_id,
                "h1_current_access_fresh_exec_runtime_manifest_id": runtime_manifest.manifest_id,
                "h1_current_access_predecision_input_set_id": input_set_id,
                "h1_current_access_predecision_context_id": replay["context_id"],
                "h1_current_access_execution_profile_id": context[
                    "h1_current_access_execution_profile_id"
                ],
                "h1_current_source_fixture_id": replay["source_id"],
                "h1_durable_proof_match_attestation_id": replay["proof_id"],
                "h1_direct_fallback_two_role_recipe_id": replay["recipe_id"],
                "h1_production_current_identity_candidate_id": replay[
                    "candidate_id"
                ],
                "h1_production_current_identity_candidate_verification_id": replay[
                    "candidate_verification_id"
                ],
                "exact_infeasibility_identity_id": context[
                    "exact_infeasibility_identity_id"
                ],
                **{name: context[name] for name in _IDENTITY_COORDINATES},
                "logical_occurrence_id": context["logical_occurrence_id"],
                "route_attempt_id": context["route_attempt_id"],
                "session_nonce": context["session_nonce"],
                "child_instance_id": child_instance,
                "broker_pid": os.getpid(),
                "child_pid": process.pid,
                "child_start_ticks": start_ticks,
                "child_pidfd_identity": _descriptor_identity(pidfd),
                "child_fd_manifest": proc_rows,
                "broker_staged_descriptor_manifest": staged_descriptor_rows,
                "scm_credentials": credentials,
                "sealed_inputs": input_rows,
                "h1_current_access_child_result_id": child_result_id,
                "child_result": child_document,
                "child_result_sha256": _sha(child_raw),
                "child_result_byte_count": len(child_raw),
                "ready_sha256": _sha(ready_raw),
                "ready_byte_count": len(ready_raw),
                "fresh_exec_observed": True,
                "distinct_child_process_observed": True,
                "exact_executable_observed": True,
                "exact_source_argv_observed": True,
                "exact_sealed_input_fd_set_observed": True,
                "scm_credentials_observed": True,
                "output_eof_observed": True,
                "zero_exit_observed": True,
                "pidfd_terminal_observed": True,
                "pidfd_reap_observed": True,
                "direct_reap_observed": True,
                "pidfd_reap_api": "waitid(P_PIDFD,WEXITED)",
                "popen_returncode_synchronized_after_pidfd_reap": True,
                "ambient_repository_path_absent": True,
                "capability_closure_complete": True,
                "same_process_private_state_adversary_resistance_claimed": False,
                "concurrent_mutation_during_checkpoint_interval_excluded": True,
                "verification_status": VERIFICATION_STATUS,
                "forbidden_operation_zero_counts": {
                    value: 0 for value in ZERO_CALL_FIELD_BY_OPERATION.values()
                },
                "caller_or_child_zero_counts_used": False,
                "common_prefix_raw_work": raw_work,
                "formal_counter_records_issued": 0,
                "production_current_access_authority_issued": False,
            }
            facts_document = {
                **facts_payload,
                "h1_current_access_observed_runtime_facts_id": content_id(
                    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
                    facts_payload,
                ),
            }
            _verify_frozen(_frozen)
            facts = H1CurrentAccessObservedRuntimeFactsV1(
                _FACTS_ISSUER, facts_document
            )
            _LIVE_FACTS[facts._facts_id] = (  # noqa: SLF001
                facts,
                canonical_json_bytes(facts_document),
            )
            return verify_h1_current_access_observed_runtime_facts_bytes_v1(
                facts.canonical_bytes,
                predecision_context_bytes=predecision_context_bytes,
                current_source_fixture_bytes=current_source_fixture_bytes,
                proof_match_attestation_bytes=proof_match_attestation_bytes,
                h1_two_role_recipe_bytes=h1_two_role_recipe_bytes,
                current_identity_candidate_bytes=current_identity_candidate_bytes,
                candidate_verification_bytes=candidate_verification_bytes,
                predecision_input_set=predecision_input_set,
            )
        except BaseException:
            if process is not None:
                _kill_and_reap(process, pidfd)
            raise
        finally:
            if child_endpoint is not None:
                child_endpoint.close()
            if parent_endpoint is not None:
                parent_endpoint.close()
            if pidfd is not None:
                os.close(pidfd)
            for descriptor in staged_fds:
                os.close(descriptor)


def _build_public_fresh_exec_runner_v1(
    implementation: Any,
    frozen: _FrozenRuntimeClosureV1,
    verifier: Any,
    prerequisite: Any,
    error_type: Any,
) -> Any:
    """Capture the import-time closure outside mutable module-name lookup."""

    implementation_code = implementation.__code__
    implementation_defaults = implementation.__defaults__
    implementation_kwdefaults = (
        None
        if implementation.__kwdefaults__ is None
        else tuple(sorted(implementation.__kwdefaults__.items()))
    )
    verifier_code = verifier.__code__
    verifier_defaults = verifier.__defaults__
    verifier_kwdefaults = (
        None
        if verifier.__kwdefaults__ is None
        else tuple(sorted(verifier.__kwdefaults__.items()))
    )
    prerequisite_code = prerequisite.__code__
    prerequisite_defaults = prerequisite.__defaults__
    prerequisite_kwdefaults = prerequisite.__kwdefaults__

    def runner(
        *,
        predecision_context_bytes: bytes,
        current_source_fixture_bytes: bytes,
        proof_match_attestation_bytes: bytes,
        h1_two_role_recipe_bytes: bytes,
        current_identity_candidate_bytes: bytes,
        candidate_verification_bytes: bytes,
        predecision_input_set: Any,
    ) -> H1CurrentAccessRuntimeUnavailableV1 | H1CurrentAccessObservedRuntimeFactsVerificationV1:
        if (
            implementation.__code__ is not implementation_code
            or implementation.__defaults__ is not implementation_defaults
            or (
                None
                if implementation.__kwdefaults__ is None
                else tuple(sorted(implementation.__kwdefaults__.items()))
            )
            != implementation_kwdefaults
            or verifier.__code__ is not verifier_code
            or verifier.__defaults__ is not verifier_defaults
            or (
                None
                if verifier.__kwdefaults__ is None
                else tuple(sorted(verifier.__kwdefaults__.items()))
            )
            != verifier_kwdefaults
            or prerequisite.__code__ is not prerequisite_code
            or prerequisite.__defaults__ is not prerequisite_defaults
            or prerequisite.__kwdefaults__ is not prerequisite_kwdefaults
        ):
            raise error_type("fresh-exec public runner closure changed after import")
        verifier(frozen)
        observed_prerequisites, prerequisite_blocker = prerequisite()
        return implementation(
            predecision_context_bytes=predecision_context_bytes,
            current_source_fixture_bytes=current_source_fixture_bytes,
            proof_match_attestation_bytes=proof_match_attestation_bytes,
            h1_two_role_recipe_bytes=h1_two_role_recipe_bytes,
            current_identity_candidate_bytes=current_identity_candidate_bytes,
            candidate_verification_bytes=candidate_verification_bytes,
            predecision_input_set=predecision_input_set,
            _frozen=frozen,
            _verify_frozen=verifier,
            _observed_prerequisites=observed_prerequisites,
            _prerequisite_blocker=prerequisite_blocker,
        )

    runner.__name__ = "run_h1_current_access_fresh_exec_runtime_v1"
    runner.__qualname__ = "run_h1_current_access_fresh_exec_runtime_v1"
    runner.__doc__ = (
        "Execute the import-time exact-source child or return typed unavailable."
    )
    return runner


run_h1_current_access_fresh_exec_runtime_v1 = _build_public_fresh_exec_runner_v1(
    _run_h1_current_access_fresh_exec_runtime_impl_v1,
    _FROZEN_RUNTIME_CLOSURE,
    _verify_frozen_runtime_closure_v1,
    _prerequisites,
    ConstructionK7H1CurrentAccessFreshExecRuntimeV1Error,
)


REQUESTED_PHASE3E_DOMAIN_TAGS = (
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_SOURCE_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_FRESH_EXEC_RUNTIME_MANIFEST_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_RUNTIME_UNAVAILABLE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_CURRENT_ACCESS_OBSERVED_RUNTIME_FACTS_VERIFICATION_V1_DOMAIN,
)
if (
    len(set(REQUESTED_PHASE3E_DOMAIN_TAGS)) != len(REQUESTED_PHASE3E_DOMAIN_TAGS)
    or not set(REQUESTED_PHASE3E_DOMAIN_TAGS) <= PHASE3E_DOMAIN_TAGS
):  # pragma: no cover
    raise RuntimeError("H1 current-access fresh-exec domains are not registered")


__all__ = (
    "FORBIDDEN_OPERATIONS",
    "H1CurrentAccessFreshExecRuntimeProfileV1",
    "H1CurrentAccessFreshExecRuntimeManifestV1",
    "H1CurrentAccessFreshExecSourceManifestV1",
    "H1CurrentAccessObservedRuntimeFactsV1",
    "H1CurrentAccessObservedRuntimeFactsVerificationV1",
    "H1CurrentAccessRuntimeUnavailableReasonV1",
    "H1CurrentAccessRuntimeUnavailableV1",
    "INPUT_ROLES",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUESTED_PHASE3E_DOMAIN_TAGS",
    "SCHEMA_VERSION",
    "VERIFICATION_STATUS",
    "official_h1_current_access_fresh_exec_runtime_profile_v1",
    "official_h1_current_access_fresh_exec_runtime_manifest_v1",
    "official_h1_current_access_fresh_exec_source_manifest_v1",
    "require_h1_current_access_fresh_exec_runtime_manifest_v1",
    "require_h1_current_access_fresh_exec_runtime_profile_v1",
    "require_h1_current_access_fresh_exec_source_manifest_v1",
    "require_h1_current_access_observed_runtime_facts_verification_v1",
    "run_h1_current_access_fresh_exec_runtime_v1",
    "verify_h1_current_access_observed_runtime_facts_bytes_v1",
)
