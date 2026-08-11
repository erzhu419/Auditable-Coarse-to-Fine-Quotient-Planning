"""Independent replay of the RAPM snapshot-to-source-bundle identity join."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_v1
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_independent_verifier_v1 as snapshot_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.107"
PROFILE_KEY = "construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1"
BINDING_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN
)
VERIFICATION_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFICATION_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({VERIFICATION_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("source-bundle binding verification domain is not central")

INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)


class ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error(
    ValueError
):
    """The claimed source-bundle binding differs from bytes-only replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty bytes")
    try:
        value = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(value) is not dict or canonical_json_bytes(value) != raw:
        _fail(f"{label} is not one canonical object")
    return value


_BINDING_FIELDS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "campaign_preregistration_verification_id",
    "campaign_preregistration_id",
    "preregistered_occurrence_spec_id",
    "occurrence_index",
    "logical_occurrence_id",
    "source_input_blob_ids",
    "complete_bundle_verification_id",
    "bundle_operational_trace_id",
    "bundle_role_digests",
    "reusable_rapm_snapshot_id",
    "source_operational_trace_id",
    "source_reusable_abstract_query_id",
    "source_final_local_replanning_id",
    "transaction_1_replanning_id",
    "transaction_2_recovery_request_id",
    "transaction_2_ground_transaction_id",
    "source_numerical_model_id",
    "source_numerical_proof_id",
    "reusable_numerical_model_id",
    "reusable_numerical_proof_id",
    "cumulative_local_ground_draw_count",
    "campaign_preregistration_exactly_replayed",
    "complete_accounting_bundle_exactly_replayed",
    "five_scientific_input_blobs_exactly_joined",
    "source_final_local_identity_joined",
    "source_occurrence_complete_bundle_binding_present",
    "snapshot_model_and_proof_typed_replay",
    "source_ground_transaction_bytes_in_bundle",
    "portable_source_ground_transaction_replay_performed",
    "scientific_planner_recomputed_by_binding",
    "source_numerical_model_identity_joined_to_bundle",
    "persistent_proof_dependency_dag_present",
    "plan_certificate_issued",
    "official_execution_allowed",
    "next_required_action",
    "query_bound_reusable_rapm_source_bundle_binding_id",
}


def _registered_inputs(
    preregistration: dict[str, Any],
    occurrence_id: str,
) -> tuple[dict[str, bytes], list[dict[str, str]], int, str]:
    matches = [
        (index, row)
        for index, row in enumerate(
            preregistration["preregistered_occurrences"], 1
        )
        if row["logical_occurrence_id"] == occurrence_id
    ]
    if len(matches) != 1:
        _fail("bundle occurrence is not registered exactly once")
    occurrence_index, occurrence = matches[0]
    blob_bytes: dict[str, bytes] = {}
    for blob in preregistration["input_blobs"]:
        raw = bytes.fromhex(blob["canonical_json_bytes_hex"])
        blob_id = blob["campaign_input_blob_id"]
        if (
            blob_id in blob_bytes
            or len(raw) != blob["byte_count"]
            or hashlib.sha256(raw).hexdigest() != blob["sha256"]
            or canonical_json_bytes(loads_canonical_json(raw)) != raw
        ):
            _fail("registered input blob changed")
        blob_bytes[blob_id] = raw
    roles = occurrence["input_roles"]
    if len(roles) != len(INPUT_ROLES):
        _fail("registered input-role cardinality changed")
    role_bytes: dict[str, bytes] = {}
    role_ids: list[dict[str, str]] = []
    for row, (role, filename) in zip(roles, INPUT_ROLES, strict=True):
        blob_id = row["campaign_input_blob_id"]
        raw = blob_bytes.get(blob_id)
        if (
            raw is None
            or row["role"] != role
            or row["filename"] != filename
            or row["byte_count"] != len(raw)
            or row["sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            _fail("registered input role changed")
        role_bytes[role] = raw
        role_ids.append({"role": role, "campaign_input_blob_id": blob_id})
    return (
        role_bytes,
        role_ids,
        occurrence_index,
        occurrence["preregistered_occurrence_spec_id"],
    )


def verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1(
    *,
    preregistration_bytes: bytes,
    bundle_directory: str | Path,
    snapshot_bytes: bytes,
    binding_bytes: bytes,
) -> dict[str, Any]:
    try:
        prereg_verification = (
            prereg_v1.verify_query_bound_campaign_preregistration_bytes_v1(
                preregistration_bytes
            )
        )
        bundle_verification = (
            bundle_v1.verify_query_bound_complete_bundle_directory_v1(
                bundle_directory
            )
        )
        snapshot = snapshot_v1.verify_query_bound_reusable_rapm_snapshot_bytes_v1(
            snapshot_bytes
        )
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error(
            "source-bundle authorities failed independent replay"
        ) from error
    preregistration = _canonical(
        preregistration_bytes,
        "campaign preregistration",
    )
    role_bytes, role_ids, occurrence_index, occurrence_spec_id = (
        _registered_inputs(
            preregistration,
            bundle_verification.occurrence_id,
        )
    )
    root = Path(bundle_directory)
    trace = _canonical(
        (root / "OPERATIONAL_TRACE.json").read_bytes(),
        "bundle operational trace",
    )
    business = _canonical(
        (root / "BUSINESS_RESULT.json").read_bytes(),
        "bundle business result",
    )
    science = trace["science_summary"]
    if business["science_summary"] != science:
        _fail("bundle science summary changed")
    expected_inventory = [
        {
            "role": role,
            "filename": filename,
            "byte_count": len(role_bytes[role]),
            "sha256": hashlib.sha256(role_bytes[role]).hexdigest(),
        }
        for role, filename in INPUT_ROLES
    ]
    if business["supervised_request"]["input_inventory"] != expected_inventory:
        _fail("bundle request crossed registered input bytes")
    source_trace = _canonical(role_bytes["SOURCE_TRACE"], "source trace")
    root_query = _canonical(role_bytes["ROOT_QUERY_RESULT"], "root query")
    if not all(
        (
            snapshot["source_logical_occurrence_id"]
            == bundle_verification.occurrence_id
            == science["occurrence_id"],
            snapshot["source_operational_trace_id"]
            == source_trace["operational_trace_id"],
            snapshot["source_reusable_abstract_query_id"]
            == root_query["reusable_abstract_query_id"],
            snapshot["source_final_local_replanning_id"]
            == science["final_local_replanning_id"],
            snapshot["transaction_1_replanning_id"]
            == science["replanning_1_id"],
            snapshot["transaction_2_recovery_request_id"]
            == science["transaction_2_request_id"],
            snapshot["transaction_2_ground_transaction_id"]
            == science["transaction_2_id"],
            snapshot["cumulative_local_ground_draw_count"]
            == science["cumulative_local_ground_draw_count"],
            prereg_verification.occurrence_ids[occurrence_index - 1]
            == snapshot["source_logical_occurrence_id"],
        )
    ):
        _fail("snapshot crossed its independently replayed source bundle")
    expected_payload = {
        "schema": "acfqp.construction_k7_query_bound_reusable_rapm_source_bundle_binding.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "campaign_preregistration_verification_id": (
            prereg_verification.verification_id
        ),
        "campaign_preregistration_id": prereg_verification.preregistration_id,
        "preregistered_occurrence_spec_id": occurrence_spec_id,
        "occurrence_index": occurrence_index,
        "logical_occurrence_id": bundle_verification.occurrence_id,
        "source_input_blob_ids": role_ids,
        "complete_bundle_verification_id": bundle_verification.verification_id,
        "bundle_operational_trace_id": bundle_verification.operational_trace_id,
        "bundle_role_digests": [
            {"artifact_role": role, "bytes_sha256": digest}
            for role, digest in bundle_verification.role_digests
        ],
        "reusable_rapm_snapshot_id": snapshot["reusable_rapm_snapshot_id"],
        "source_operational_trace_id": snapshot["source_operational_trace_id"],
        "source_reusable_abstract_query_id": snapshot[
            "source_reusable_abstract_query_id"
        ],
        "source_final_local_replanning_id": snapshot[
            "source_final_local_replanning_id"
        ],
        "transaction_1_replanning_id": snapshot["transaction_1_replanning_id"],
        "transaction_2_recovery_request_id": snapshot[
            "transaction_2_recovery_request_id"
        ],
        "transaction_2_ground_transaction_id": snapshot[
            "transaction_2_ground_transaction_id"
        ],
        "source_numerical_model_id": snapshot["source_numerical_model_id"],
        "source_numerical_proof_id": snapshot["source_numerical_proof_id"],
        "reusable_numerical_model_id": snapshot["reusable_numerical_model_id"],
        "reusable_numerical_proof_id": snapshot["reusable_numerical_proof_id"],
        "cumulative_local_ground_draw_count": snapshot[
            "cumulative_local_ground_draw_count"
        ],
        "campaign_preregistration_exactly_replayed": True,
        "complete_accounting_bundle_exactly_replayed": True,
        "five_scientific_input_blobs_exactly_joined": True,
        "source_final_local_identity_joined": True,
        "source_occurrence_complete_bundle_binding_present": True,
        "snapshot_model_and_proof_typed_replay": True,
        "source_ground_transaction_bytes_in_bundle": False,
        "portable_source_ground_transaction_replay_performed": False,
        "scientific_planner_recomputed_by_binding": False,
        "source_numerical_model_identity_joined_to_bundle": False,
        "persistent_proof_dependency_dag_present": False,
        "plan_certificate_issued": False,
        "official_execution_allowed": False,
        "next_required_action": (
            "MATERIALIZE_IDENTITY_BOUND_PROOF_DEPENDENCY_DAG"
        ),
    }
    binding = _canonical(binding_bytes, "source-bundle binding")
    require_exact_fields(
        binding,
        _BINDING_FIELDS,
        context="source-bundle binding",
    )
    binding_id = binding["query_bound_reusable_rapm_source_bundle_binding_id"]
    _cid(binding_id, "source-bundle binding")
    if (
        binding != {**expected_payload, "query_bound_reusable_rapm_source_bundle_binding_id": binding_id}
        or binding_id != content_id(BINDING_DOMAIN, expected_payload)
    ):
        _fail("source-bundle binding differs from independent replay")
    verification_payload = {
        "schema": "acfqp.construction_k7_query_bound_reusable_rapm_source_bundle_binding_verification.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "source_bundle_binding_id": binding_id,
        "campaign_preregistration_verification_id": (
            prereg_verification.verification_id
        ),
        "complete_bundle_verification_id": bundle_verification.verification_id,
        "reusable_rapm_snapshot_id": snapshot["reusable_rapm_snapshot_id"],
        "logical_occurrence_id": bundle_verification.occurrence_id,
        "source_final_local_replanning_id": snapshot[
            "source_final_local_replanning_id"
        ],
        "reusable_numerical_model_id": snapshot["reusable_numerical_model_id"],
        "reusable_numerical_proof_id": snapshot["reusable_numerical_proof_id"],
        "preregistration_bundle_snapshot_join_replayed": True,
        "source_occurrence_complete_bundle_binding_verified": True,
        "source_ground_transaction_replay_performed": False,
        "persistent_proof_dependency_dag_verified": False,
        "plan_certificate_verified": False,
        "official_execution_allowed": False,
        "verification_result": "REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_VERIFIED",
        "next_required_action": (
            "MATERIALIZE_IDENTITY_BOUND_PROOF_DEPENDENCY_DAG"
        ),
    }
    return {
        **verification_payload,
        "query_bound_reusable_rapm_source_bundle_binding_verification_id": content_id(
            VERIFICATION_DOMAIN,
            verification_payload,
        ),
    }


__all__ = [
    "ConstructionK7QueryBoundReusableRAPMSourceBundleBindingIndependentVerifierV1Error",
    "LOCAL_DOMAINS",
    "verify_query_bound_reusable_rapm_source_bundle_binding_bytes_v1",
]
