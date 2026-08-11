"""Bind one reusable RAPM snapshot to its verified source occurrence bundle."""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
from typing import Any, NoReturn

from acfqp import construction_k7_query_bound_campaign_preregistration_independent_verifier_v1 as prereg_v1
from acfqp import construction_k7_query_bound_complete_bundle_independent_verifier_v1 as bundle_v1
from acfqp import construction_k7_query_bound_reusable_rapm_snapshot_v1 as snapshot_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.107"
PROFILE_KEY = "construction_k7_query_bound_reusable_rapm_source_bundle_binding_v1"
BINDING_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_REUSABLE_RAPM_SOURCE_BUNDLE_BINDING_V1_DOMAIN
)
LOCAL_DOMAINS = frozenset({BINDING_DOMAIN})
if not LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS:  # pragma: no cover
    raise RuntimeError("reusable RAPM source-bundle domain is not central")

INPUT_ROLES = (
    ("SOURCE_TRACE", "source_trace.json"),
    ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
    ("ROOT_QUERY_RESULT", "root_query_result.json"),
    ("RECOVERY_OVERLAY", "recovery_overlay.json"),
    ("RECOVERY_REQUEST", "recovery_request.json"),
)
_ISSUER = object()


class ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
    ValueError
):
    """The preregistration, source bundle, or RAPM lineage crossed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
        message
    )


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _canonical(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw:
        _fail(f"{label} must be nonempty bytes")
    try:
        document = loads_canonical_json(raw)
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
            f"{label} is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(f"{label} is not one canonical object")
    return document


def _source_inputs(
    *,
    preregistration: dict[str, Any],
    occurrence_id: str,
) -> tuple[dict[str, bytes], tuple[tuple[str, str], ...], int, str]:
    occurrences = preregistration["preregistered_occurrences"]
    matches = [
        (index, row)
        for index, row in enumerate(occurrences, 1)
        if row["logical_occurrence_id"] == occurrence_id
    ]
    if len(matches) != 1:
        _fail("source bundle occurrence is not registered exactly once")
    occurrence_index, occurrence = matches[0]
    blobs: dict[str, bytes] = {}
    for blob in preregistration["input_blobs"]:
        try:
            raw = bytes.fromhex(blob["canonical_json_bytes_hex"])
        except (KeyError, TypeError, ValueError) as error:
            raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
                "campaign input blob bytes changed"
            ) from error
        blob_id = blob["campaign_input_blob_id"]
        if (
            blob_id in blobs
            or len(raw) != blob["byte_count"]
            or hashlib.sha256(raw).hexdigest() != blob["sha256"]
            or canonical_json_bytes(loads_canonical_json(raw)) != raw
        ):
            _fail("campaign input blob identity changed")
        blobs[blob_id] = raw
    rows = occurrence["input_roles"]
    if len(rows) != len(INPUT_ROLES):
        _fail("source occurrence input-role cardinality changed")
    role_bytes: dict[str, bytes] = {}
    role_blob_ids: list[tuple[str, str]] = []
    for row, (expected_role, expected_filename) in zip(
        rows, INPUT_ROLES, strict=True
    ):
        blob_id = row["campaign_input_blob_id"]
        raw = blobs.get(blob_id)
        if (
            row["role"] != expected_role
            or row["filename"] != expected_filename
            or raw is None
            or row["byte_count"] != len(raw)
            or row["sha256"] != hashlib.sha256(raw).hexdigest()
        ):
            _fail("source occurrence input role changed")
        role_bytes[expected_role] = raw
        role_blob_ids.append((expected_role, blob_id))
    return (
        role_bytes,
        tuple(role_blob_ids),
        occurrence_index,
        occurrence["preregistered_occurrence_spec_id"],
    )


@dataclass(frozen=True, slots=True)
class QueryBoundReusableRAPMSourceBundleBindingV1:
    _issuer: InitVar[object]
    campaign_preregistration_verification_id: str
    campaign_preregistration_id: str
    preregistered_occurrence_spec_id: str
    occurrence_index: int
    occurrence_id: str
    source_input_blob_ids: tuple[tuple[str, str], ...]
    complete_bundle_verification_id: str
    bundle_operational_trace_id: str
    bundle_role_digests: tuple[tuple[str, str], ...]
    reusable_rapm_snapshot_id: str
    source_operational_trace_id: str
    source_reusable_abstract_query_id: str
    source_final_local_replanning_id: str
    transaction_1_replanning_id: str
    transaction_2_recovery_request_id: str
    transaction_2_ground_transaction_id: str
    source_numerical_model_id: str
    source_numerical_proof_id: str
    reusable_numerical_model_id: str
    reusable_numerical_proof_id: str
    cumulative_local_ground_draw_count: int
    _binding_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ISSUER:
            _fail("reusable RAPM source-bundle binding is caller-minted")
        for value, label in (
            (self.campaign_preregistration_verification_id, "preregistration verification"),
            (self.campaign_preregistration_id, "campaign preregistration"),
            (self.preregistered_occurrence_spec_id, "occurrence spec"),
            (self.occurrence_id, "occurrence"),
            (self.complete_bundle_verification_id, "complete-bundle verification"),
            (self.bundle_operational_trace_id, "bundle operational trace"),
            (self.reusable_rapm_snapshot_id, "reusable RAPM snapshot"),
            (self.source_operational_trace_id, "source operational trace"),
            (self.source_reusable_abstract_query_id, "source abstract query"),
            (self.source_final_local_replanning_id, "source final replanning"),
            (self.transaction_1_replanning_id, "transaction-1 replanning"),
            (self.transaction_2_recovery_request_id, "transaction-2 request"),
            (self.transaction_2_ground_transaction_id, "transaction-2 result"),
            (self.source_numerical_model_id, "source numerical model"),
            (self.source_numerical_proof_id, "source numerical proof"),
            (self.reusable_numerical_model_id, "reusable numerical model"),
            (self.reusable_numerical_proof_id, "reusable numerical proof"),
            *((value, "source input blob") for _role, value in self.source_input_blob_ids),
            *((value, "bundle role digest") for _role, value in self.bundle_role_digests),
        ):
            _cid(value, label)
        if (
            type(self.occurrence_index) is not int
            or self.occurrence_index <= 0
            or type(self.cumulative_local_ground_draw_count) is not int
            or self.cumulative_local_ground_draw_count <= 0
            or tuple(role for role, _value in self.source_input_blob_ids)
            != tuple(role for role, _filename in INPUT_ROLES)
            or len(self.bundle_role_digests) != 8
        ):
            _fail("reusable RAPM source-bundle inventory changed")
        object.__setattr__(
            self,
            "_binding_id",
            content_id(BINDING_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_reusable_rapm_source_bundle_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "campaign_preregistration_verification_id": (
                self.campaign_preregistration_verification_id
            ),
            "campaign_preregistration_id": self.campaign_preregistration_id,
            "preregistered_occurrence_spec_id": (
                self.preregistered_occurrence_spec_id
            ),
            "occurrence_index": self.occurrence_index,
            "logical_occurrence_id": self.occurrence_id,
            "source_input_blob_ids": [
                {"role": role, "campaign_input_blob_id": blob_id}
                for role, blob_id in self.source_input_blob_ids
            ],
            "complete_bundle_verification_id": (
                self.complete_bundle_verification_id
            ),
            "bundle_operational_trace_id": self.bundle_operational_trace_id,
            "bundle_role_digests": [
                {"artifact_role": role, "bytes_sha256": digest}
                for role, digest in self.bundle_role_digests
            ],
            "reusable_rapm_snapshot_id": self.reusable_rapm_snapshot_id,
            "source_operational_trace_id": self.source_operational_trace_id,
            "source_reusable_abstract_query_id": (
                self.source_reusable_abstract_query_id
            ),
            "source_final_local_replanning_id": (
                self.source_final_local_replanning_id
            ),
            "transaction_1_replanning_id": self.transaction_1_replanning_id,
            "transaction_2_recovery_request_id": (
                self.transaction_2_recovery_request_id
            ),
            "transaction_2_ground_transaction_id": (
                self.transaction_2_ground_transaction_id
            ),
            "source_numerical_model_id": self.source_numerical_model_id,
            "source_numerical_proof_id": self.source_numerical_proof_id,
            "reusable_numerical_model_id": self.reusable_numerical_model_id,
            "reusable_numerical_proof_id": self.reusable_numerical_proof_id,
            "cumulative_local_ground_draw_count": (
                self.cumulative_local_ground_draw_count
            ),
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

    @property
    def binding_id(self) -> str:
        current = content_id(BINDING_DOMAIN, self._payload())
        if current != self._binding_id:
            _fail("reusable RAPM source-bundle binding changed after issuance")
        return current

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "query_bound_reusable_rapm_source_bundle_binding_id": self.binding_id,
        }


def bind_query_bound_reusable_rapm_source_bundle_v1(
    *,
    preregistration_bytes: bytes,
    bundle_directory: str | Path,
    snapshot_bytes: bytes,
) -> QueryBoundReusableRAPMSourceBundleBindingV1:
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
        snapshot = snapshot_v1.replay_query_bound_reusable_rapm_snapshot_bytes_v1(
            snapshot_bytes
        )
    except Exception as error:
        raise ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error(
            "reusable RAPM source authorities failed replay"
        ) from error
    preregistration = _canonical(
        preregistration_bytes,
        "campaign preregistration",
    )
    role_bytes, role_blob_ids, occurrence_index, occurrence_spec_id = (
        _source_inputs(
            preregistration=preregistration,
            occurrence_id=bundle_verification.occurrence_id,
        )
    )
    root = Path(bundle_directory)
    trace_raw = (root / "OPERATIONAL_TRACE.json").read_bytes()
    business_raw = (root / "BUSINESS_RESULT.json").read_bytes()
    trace = _canonical(trace_raw, "bundle operational trace")
    business = _canonical(business_raw, "bundle business result")
    science = trace["science_summary"]
    if business["science_summary"] != science:
        _fail("bundle science summary crossed its operational trace")
    inventory = business["supervised_request"]["input_inventory"]
    expected_inventory = [
        {
            "role": role,
            "filename": filename,
            "byte_count": len(role_bytes[role]),
            "sha256": hashlib.sha256(role_bytes[role]).hexdigest(),
        }
        for role, filename in INPUT_ROLES
    ]
    if inventory != expected_inventory:
        _fail("bundle request crossed preregistered scientific inputs")
    source_trace = _canonical(role_bytes["SOURCE_TRACE"], "source trace")
    root_query = _canonical(role_bytes["ROOT_QUERY_RESULT"], "root query")
    joins = (
        snapshot.source_logical_occurrence_id
        == bundle_verification.occurrence_id
        == science["occurrence_id"],
        snapshot.source_operational_trace_id
        == source_trace["operational_trace_id"],
        snapshot.source_reusable_abstract_query_id
        == root_query["reusable_abstract_query_id"],
        snapshot.source_final_local_replanning_id
        == science["final_local_replanning_id"],
        snapshot.transaction_1_replanning_id == science["replanning_1_id"],
        snapshot.transaction_2_recovery_request_id
        == science["transaction_2_request_id"],
        snapshot.transaction_2_ground_transaction_id
        == science["transaction_2_id"],
        snapshot.cumulative_local_ground_draw_count
        == science["cumulative_local_ground_draw_count"],
        prereg_verification.occurrence_ids[occurrence_index - 1]
        == snapshot.source_logical_occurrence_id,
    )
    if not all(joins):
        _fail("reusable RAPM snapshot crossed its registered source bundle")
    return QueryBoundReusableRAPMSourceBundleBindingV1(
        _ISSUER,
        prereg_verification.verification_id,
        prereg_verification.preregistration_id,
        occurrence_spec_id,
        occurrence_index,
        bundle_verification.occurrence_id,
        role_blob_ids,
        bundle_verification.verification_id,
        bundle_verification.operational_trace_id,
        bundle_verification.role_digests,
        snapshot.snapshot_id,
        snapshot.source_operational_trace_id,
        snapshot.source_reusable_abstract_query_id,
        snapshot.source_final_local_replanning_id,
        snapshot.transaction_1_replanning_id,
        snapshot.transaction_2_recovery_request_id,
        snapshot.transaction_2_ground_transaction_id,
        snapshot.source_numerical_model_id,
        snapshot.source_numerical_proof_id,
        snapshot.reusable_model.model_id,
        snapshot.reusable_proof.proof_id,
        snapshot.cumulative_local_ground_draw_count,
    )


__all__ = [
    "ConstructionK7QueryBoundReusableRAPMSourceBundleBindingV1Error",
    "LOCAL_DOMAINS",
    "QueryBoundReusableRAPMSourceBundleBindingV1",
    "bind_query_bound_reusable_rapm_source_bundle_v1",
]
