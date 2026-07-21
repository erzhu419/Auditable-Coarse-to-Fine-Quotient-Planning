"""Independent transport for the first Phase-3E H2 failure-prefix slice.

This module deliberately stops before ground binding, route selection, terminal
classification, and occurrence closure.  It persists enough immutable bytes to
replay the H2 model-only ``FAIL`` and its native common-prefix accounting in a
fresh verifier process.  Runtime authority tokens are neither serialized nor
reconstructed from transport bytes.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Any

from acfqp.accounting_v1 import (
    ComparisonProfileV1,
    ComparisonVectorV1,
    CounterRegistryV1,
    NativeZeroAttestationV1,
    ReconciliationProofV1,
    WorkVectorV1,
    official_comparison_profile_v1,
    official_counter_registry_v1,
)
from acfqp.actual_accounting_v1 import ActualProjectionProofV1, ActualWorkScope
from acfqp.campaign_v1 import LogicalOccurrenceV1, RouteAttemptV1
from acfqp.native_recorder_v1 import RecordedWorkV1, verify_recorded_work_v1
from acfqp.phase3e_ids import (
    LOGICAL_OCCURRENCE_DOMAIN,
    MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
    MODEL_ONLY_RESULT_DOMAIN,
    PHASE3E_BUNDLE_MANIFEST_DOMAIN,
    RECORDED_WORK_TRANSPORT_DOMAIN,
    ROUTE_ATTEMPT_DOMAIN,
    ROUTE_DECISION_CONTEXT_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
    require_exact_fields,
    require_registered_domain_tag,
)
from acfqp.phase3e_model_only_executor_v1 import (
    EXECUTION_SCHEMA,
    REQUEST_SCHEMA,
    ModelOnlyExecutionRequestV1,
    ModelOnlyQueryExecutionArtifactV1,
    ModelOnlyQueryExecutionV1,
    parse_model_only_execution_request_v1,
    verify_model_only_failed_prefix_artifact_v1,
    verify_model_only_failed_prefix_execution_v1,
)
from acfqp.phase3e_model_only_v1 import MODEL_ONLY_RESULT_SCHEMA
from acfqp.phase3e_rapm_consumer_v1 import (
    LOCAL_QUERY_KEY,
    load_phase3c_model_source_v1,
)
from acfqp.routing_v1 import RouteDecisionContextV1, TypedNotApplicable


SCHEMA_VERSION = "1.0.0"
RECORDED_WORK_TRANSPORT_SCHEMA = "acfqp.recorded_work_transport.v1"
BUNDLE_ENTRY_SCHEMA = "acfqp.phase3e_bundle_entry.v1"
BUNDLE_MANIFEST_SCHEMA = "acfqp.phase3e_bundle_manifest.v1"
BUNDLE_SCOPE = "H2_MODEL_FAILURE_PREFIX_ONLY"
VERIFICATION_STATUS = "VERIFIED_MODEL_FAILURE_PREFIX"
NOT_RUN = "NOT_RUN"

TERMINAL_NOT_APPLICABLE_REASON = (
    "the H2 model failure prefix is not a terminal certificate"
)
OCCURRENCE_NOT_APPLICABLE_REASON = (
    "the H2 model failure prefix has not closed its logical occurrence"
)

REMAINING_BLOCKERS = (
    "GROUND_BINDING_NOT_OPENED",
    "SELECTED_ROUTE_NOT_RUN",
    "SELECTED_ROUTE_EXECUTION_RECEIPT_NOT_BUNDLED",
    "TERMINAL_CLASSIFICATION_NOT_RUN",
    "OCCURRENCE_CLOSURE_NOT_RUN",
    "CAMPAIGN_CLOSURE_NOT_RUN",
)

MANIFEST_FILENAME = "manifest.json"
MANIFEST_CHECKSUM_FILENAME = "manifest.sha256"
_MAX_DOCUMENT_BYTES = 64 * 1024 * 1024


class Phase3EBundleV1Error(ValueError):
    """A bundle path, byte digest, schema, identity, or replay is invalid."""


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _content_hash(value: Any, field_name: str) -> str:
    try:
        return parse_content_id(value)
    except ValueError as error:
        raise Phase3EBundleV1Error(
            f"{field_name} must be a full lowercase SHA-256"
        ) from error


def _nonempty_text(value: Any, field_name: str) -> str:
    if type(value) is not str or not value:
        raise Phase3EBundleV1Error(f"{field_name} must be nonempty text")
    return value


def _safe_relative_path(value: Any) -> str:
    if type(value) is not str or not value or "\\" in value:
        raise Phase3EBundleV1Error("bundle entry path must be a POSIX relative path")
    parts = value.split("/")
    if value.startswith("/") or any(part in {"", ".", ".."} for part in parts):
        raise Phase3EBundleV1Error("bundle entry path traversal is forbidden")
    return value


def _plain_canonical_object(raw: bytes, *, source: str) -> dict[str, Any]:
    if len(raw) > _MAX_DOCUMENT_BYTES:
        raise Phase3EBundleV1Error(f"{source} exceeds the bundle document cap")
    try:
        loads_canonical_json(raw)
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        raise Phase3EBundleV1Error(
            f"{source} is not canonical JSON: {error}"
        ) from error
    if type(value) is not dict:
        raise Phase3EBundleV1Error(f"{source} root must be an object")
    return value


def _recorded_work_payload_v1(work: RecordedWorkV1) -> dict[str, Any]:
    return {
        "schema": RECORDED_WORK_TRANSPORT_SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "work_vector": work.work_vector.to_dict(),
        "native_zero_attestation": work.native_zero_attestation.to_dict(),
        "reconciliation_proof": work.reconciliation_proof.to_dict(),
        "comparison_vector": work.comparison_vector.to_dict(),
        "actual_projection_proof": work.actual_projection_proof.to_dict(),
    }


def recorded_work_transport_id_v1(work: RecordedWorkV1) -> str:
    return content_id(
        RECORDED_WORK_TRANSPORT_DOMAIN, _recorded_work_payload_v1(work)
    )


def recorded_work_to_dict_v1(
    work: RecordedWorkV1,
    *,
    expected_scope: ActualWorkScope | str | None = None,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> dict[str, Any]:
    """Serialize all five native-work constituents after exact replay."""

    if type(work) is not RecordedWorkV1:
        raise Phase3EBundleV1Error("recorded work has the wrong runtime type")
    selected_registry = registry or official_counter_registry_v1()
    selected_profile = comparison_profile or official_comparison_profile_v1(
        selected_registry
    )
    scope = work.actual_projection_proof.work_scope
    if expected_scope is not None and scope is not ActualWorkScope(expected_scope):
        raise Phase3EBundleV1Error("recorded work has an unexpected work scope")
    try:
        verify_recorded_work_v1(
            work,
            expected_scope=scope,
            registry=selected_registry,
            comparison_profile=selected_profile,
        )
    except ValueError as error:
        raise Phase3EBundleV1Error(
            f"recorded work does not replay: {error}"
        ) from error
    payload = _recorded_work_payload_v1(work)
    return {
        **payload,
        "recorded_work_transport_id": content_id(
            RECORDED_WORK_TRANSPORT_DOMAIN, payload
        ),
    }


def recorded_work_from_dict_v1(
    document: Mapping[str, Any],
    *,
    expected_scope: ActualWorkScope | str,
    registry: CounterRegistryV1 | None = None,
    comparison_profile: ComparisonProfileV1 | None = None,
) -> RecordedWorkV1:
    """Strictly parse and replay every native-work constituent."""

    try:
        require_exact_fields(
            document,
            {
                "schema",
                "schema_version",
                "work_vector",
                "native_zero_attestation",
                "reconciliation_proof",
                "comparison_vector",
                "actual_projection_proof",
                "recorded_work_transport_id",
            },
            context="RecordedWorkV1 transport",
        )
    except ValueError as error:
        raise Phase3EBundleV1Error(str(error)) from error
    if (
        document["schema"] != RECORDED_WORK_TRANSPORT_SCHEMA
        or document["schema_version"] != SCHEMA_VERSION
    ):
        raise Phase3EBundleV1Error("recorded-work transport schema mismatch")
    selected_registry = registry or official_counter_registry_v1()
    selected_profile = comparison_profile or official_comparison_profile_v1(
        selected_registry
    )
    try:
        work = RecordedWorkV1(
            WorkVectorV1.from_dict(document["work_vector"], selected_registry),
            NativeZeroAttestationV1.from_dict(
                document["native_zero_attestation"]
            ),
            ReconciliationProofV1.from_dict(document["reconciliation_proof"]),
            ComparisonVectorV1.from_dict(document["comparison_vector"]),
            ActualProjectionProofV1.from_dict(
                document["actual_projection_proof"]
            ),
        )
        verified = verify_recorded_work_v1(
            work,
            expected_scope=expected_scope,
            registry=selected_registry,
            comparison_profile=selected_profile,
        )
    except (TypeError, ValueError) as error:
        raise Phase3EBundleV1Error(
            f"recorded-work transport replay failed: {error}"
        ) from error
    payload = _recorded_work_payload_v1(verified)
    if document["recorded_work_transport_id"] != content_id(
        RECORDED_WORK_TRANSPORT_DOMAIN, payload
    ):
        raise Phase3EBundleV1Error("recorded-work transport content ID mismatch")
    return verified


class Phase3EBundleRoleV1(str, Enum):
    MODEL_ONLY_REQUEST = "MODEL_ONLY_REQUEST"
    MODEL_ONLY_EXECUTION = "MODEL_ONLY_EXECUTION"
    MODEL_ONLY_RESULT = "MODEL_ONLY_RESULT"
    ROUTE_DECISION_CONTEXT = "ROUTE_DECISION_CONTEXT"
    LOGICAL_OCCURRENCE = "LOGICAL_OCCURRENCE"
    ROUTE_ATTEMPT = "ROUTE_ATTEMPT"
    COMMON_PREFIX_RECORDED_WORK = "COMMON_PREFIX_RECORDED_WORK"


@dataclass(frozen=True, slots=True)
class _RoleSpecV1:
    schema_id: str
    domain_tag: str
    relative_path: str


_ROLE_SPECS: dict[Phase3EBundleRoleV1, _RoleSpecV1] = {
    Phase3EBundleRoleV1.MODEL_ONLY_REQUEST: _RoleSpecV1(
        REQUEST_SCHEMA,
        MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
        "model_only/request.json",
    ),
    Phase3EBundleRoleV1.MODEL_ONLY_EXECUTION: _RoleSpecV1(
        EXECUTION_SCHEMA,
        MODEL_ONLY_ORCHESTRATION_BINDING_DOMAIN,
        "model_only/execution.json",
    ),
    Phase3EBundleRoleV1.MODEL_ONLY_RESULT: _RoleSpecV1(
        MODEL_ONLY_RESULT_SCHEMA,
        MODEL_ONLY_RESULT_DOMAIN,
        "model_only/result.json",
    ),
    Phase3EBundleRoleV1.ROUTE_DECISION_CONTEXT: _RoleSpecV1(
        "acfqp.route_decision_context.v1",
        ROUTE_DECISION_CONTEXT_DOMAIN,
        "routing/route_context.json",
    ),
    Phase3EBundleRoleV1.LOGICAL_OCCURRENCE: _RoleSpecV1(
        "acfqp.logical_occurrence.v1",
        LOGICAL_OCCURRENCE_DOMAIN,
        "campaign/logical_occurrence.json",
    ),
    Phase3EBundleRoleV1.ROUTE_ATTEMPT: _RoleSpecV1(
        "acfqp.route_attempt.v1",
        ROUTE_ATTEMPT_DOMAIN,
        "campaign/route_attempt.json",
    ),
    Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK: _RoleSpecV1(
        RECORDED_WORK_TRANSPORT_SCHEMA,
        RECORDED_WORK_TRANSPORT_DOMAIN,
        "accounting/common_prefix_recorded_work.json",
    ),
}


@dataclass(frozen=True, slots=True)
class Phase3EBundleEntryV1:
    role: Phase3EBundleRoleV1
    schema_id: str
    domain_tag: str
    content_id: str
    relative_path: str
    sha256: str
    size_bytes: int

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "role", Phase3EBundleRoleV1(self.role))
            require_registered_domain_tag(self.domain_tag)
        except (TypeError, ValueError) as error:
            raise Phase3EBundleV1Error(
                f"invalid bundle entry role/domain: {error}"
            ) from error
        _nonempty_text(self.schema_id, "schema_id")
        _content_hash(self.content_id, "content_id")
        object.__setattr__(
            self, "relative_path", _safe_relative_path(self.relative_path)
        )
        _content_hash(self.sha256, "sha256")
        if type(self.size_bytes) is not int or self.size_bytes < 0:
            raise Phase3EBundleV1Error("entry size_bytes must be nonnegative")
        spec = _ROLE_SPECS[self.role]
        if (
            self.schema_id,
            self.domain_tag,
            self.relative_path,
        ) != (spec.schema_id, spec.domain_tag, spec.relative_path):
            raise Phase3EBundleV1Error(
                "bundle entry role/schema/domain/path binding mismatch"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_ENTRY_SCHEMA,
            "schema_version": SCHEMA_VERSION,
            "role": self.role.value,
            "schema_id": self.schema_id,
            "domain_tag": self.domain_tag,
            "content_id": self.content_id,
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }

    @classmethod
    def from_dict(cls, document: Mapping[str, Any]) -> "Phase3EBundleEntryV1":
        try:
            require_exact_fields(
                document,
                {
                    "schema",
                    "schema_version",
                    "role",
                    "schema_id",
                    "domain_tag",
                    "content_id",
                    "relative_path",
                    "sha256",
                    "size_bytes",
                },
                context="Phase3E bundle entry",
            )
        except ValueError as error:
            raise Phase3EBundleV1Error(str(error)) from error
        if (
            document["schema"] != BUNDLE_ENTRY_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
        ):
            raise Phase3EBundleV1Error("bundle entry schema mismatch")
        return cls(
            document["role"],
            document["schema_id"],
            document["domain_tag"],
            document["content_id"],
            document["relative_path"],
            document["sha256"],
            document["size_bytes"],
        )


@dataclass(frozen=True, slots=True)
class Phase3EBundleManifestV1:
    source_bundle_sha256: str
    source_manifest_sha256: str
    source_lease_id: str
    query_key: str
    model_only_request_id: str
    model_only_execution_id: str
    model_only_result_id: str
    route_decision_context_id: str
    logical_occurrence_id: str
    route_attempt_id: str
    common_prefix_work_vector_id: str
    terminal_artifact_id: TypedNotApplicable
    occurrence_closure_id: TypedNotApplicable
    entries: tuple[Phase3EBundleEntryV1, ...]
    bundle_scope: str = BUNDLE_SCOPE
    verification_status: str = VERIFICATION_STATUS
    model_only_outcome: str = "FAIL"
    selected_route_status: str = NOT_RUN
    terminal_status: str = NOT_RUN
    occurrence_closure_status: str = NOT_RUN
    remaining_blockers: tuple[str, ...] = REMAINING_BLOCKERS
    official_execution_allowed: bool = False
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        for field_name in (
            "source_bundle_sha256",
            "source_manifest_sha256",
            "source_lease_id",
            "model_only_request_id",
            "model_only_execution_id",
            "model_only_result_id",
            "route_decision_context_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "common_prefix_work_vector_id",
        ):
            _content_hash(getattr(self, field_name), field_name)
        if self.query_key != LOCAL_QUERY_KEY:
            raise Phase3EBundleV1Error(
                "failed-prefix bundle must bind the H2 query key"
            )
        if (
            type(self.terminal_artifact_id) is not TypedNotApplicable
            or self.terminal_artifact_id.reason != TERMINAL_NOT_APPLICABLE_REASON
            or type(self.occurrence_closure_id) is not TypedNotApplicable
            or self.occurrence_closure_id.reason
            != OCCURRENCE_NOT_APPLICABLE_REASON
        ):
            raise Phase3EBundleV1Error(
                "failed-prefix terminal/occurrence references must be typed "
                "not-applicable"
            )
        if type(self.entries) is not tuple or len(self.entries) != len(_ROLE_SPECS):
            raise Phase3EBundleV1Error("bundle manifest has missing or extra entries")
        if not all(type(entry) is Phase3EBundleEntryV1 for entry in self.entries):
            raise Phase3EBundleV1Error(
                "bundle manifest entries must be exact typed entries"
            )
        if (
            tuple(sorted(self.entries, key=lambda row: row.relative_path))
            != self.entries
        ):
            raise Phase3EBundleV1Error("bundle entries must be path-sorted")
        if {entry.role for entry in self.entries} != set(_ROLE_SPECS):
            raise Phase3EBundleV1Error("bundle roles are incomplete or duplicated")
        if len({entry.relative_path for entry in self.entries}) != len(self.entries):
            raise Phase3EBundleV1Error("bundle repeats an entry path")
        if len({entry.content_id for entry in self.entries}) != len(self.entries):
            raise Phase3EBundleV1Error("bundle reuses one content ID across roles")
        fixed = (
            self.bundle_scope == BUNDLE_SCOPE,
            self.verification_status == VERIFICATION_STATUS,
            self.model_only_outcome == "FAIL",
            self.selected_route_status == NOT_RUN,
            self.terminal_status == NOT_RUN,
            self.occurrence_closure_status == NOT_RUN,
            self.remaining_blockers == REMAINING_BLOCKERS,
            self.official_execution_allowed is False,
            self.schema_version == SCHEMA_VERSION,
        )
        if not all(fixed):
            raise Phase3EBundleV1Error(
                "failed-prefix scope, lock, status, or blocker fields changed"
            )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": BUNDLE_MANIFEST_SCHEMA,
            "schema_version": self.schema_version,
            "bundle_scope": self.bundle_scope,
            "verification_status": self.verification_status,
            "source_bundle_sha256": self.source_bundle_sha256,
            "source_manifest_sha256": self.source_manifest_sha256,
            "source_lease_id": self.source_lease_id,
            "query_key": self.query_key,
            "model_only_request_id": self.model_only_request_id,
            "model_only_execution_id": self.model_only_execution_id,
            "model_only_result_id": self.model_only_result_id,
            "RouteDecisionContext_id": self.route_decision_context_id,
            "logical_occurrence_id": self.logical_occurrence_id,
            "route_attempt_id": self.route_attempt_id,
            "common_prefix_work_vector_id": self.common_prefix_work_vector_id,
            "model_only_outcome": self.model_only_outcome,
            "selected_route_status": self.selected_route_status,
            "terminal_status": self.terminal_status,
            "occurrence_closure_status": self.occurrence_closure_status,
            "terminal_artifact_id": self.terminal_artifact_id.to_dict(),
            "occurrence_closure_id": self.occurrence_closure_id.to_dict(),
            "remaining_blockers": list(self.remaining_blockers),
            "official_execution_allowed": False,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @property
    def phase3e_bundle_manifest_id(self) -> str:
        return content_id(PHASE3E_BUNDLE_MANIFEST_DOMAIN, self._payload())

    def to_dict(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "phase3e_bundle_manifest_id": self.phase3e_bundle_manifest_id,
        }

    @classmethod
    def from_dict(
        cls, document: Mapping[str, Any]
    ) -> "Phase3EBundleManifestV1":
        fields = {
            "schema",
            "schema_version",
            "bundle_scope",
            "verification_status",
            "source_bundle_sha256",
            "source_manifest_sha256",
            "source_lease_id",
            "query_key",
            "model_only_request_id",
            "model_only_execution_id",
            "model_only_result_id",
            "RouteDecisionContext_id",
            "logical_occurrence_id",
            "route_attempt_id",
            "common_prefix_work_vector_id",
            "model_only_outcome",
            "selected_route_status",
            "terminal_status",
            "occurrence_closure_status",
            "terminal_artifact_id",
            "occurrence_closure_id",
            "remaining_blockers",
            "official_execution_allowed",
            "entries",
            "phase3e_bundle_manifest_id",
        }
        try:
            require_exact_fields(document, fields, context="Phase3E bundle manifest")
        except ValueError as error:
            raise Phase3EBundleV1Error(str(error)) from error
        if (
            document["schema"] != BUNDLE_MANIFEST_SCHEMA
            or document["schema_version"] != SCHEMA_VERSION
            or type(document["entries"]) is not list
            or type(document["remaining_blockers"]) is not list
        ):
            raise Phase3EBundleV1Error("bundle manifest schema mismatch")
        try:
            result = cls(
                document["source_bundle_sha256"],
                document["source_manifest_sha256"],
                document["source_lease_id"],
                document["query_key"],
                document["model_only_request_id"],
                document["model_only_execution_id"],
                document["model_only_result_id"],
                document["RouteDecisionContext_id"],
                document["logical_occurrence_id"],
                document["route_attempt_id"],
                document["common_prefix_work_vector_id"],
                TypedNotApplicable.from_dict(document["terminal_artifact_id"]),
                TypedNotApplicable.from_dict(document["occurrence_closure_id"]),
                tuple(
                    Phase3EBundleEntryV1.from_dict(row)
                    for row in document["entries"]
                ),
                document["bundle_scope"],
                document["verification_status"],
                document["model_only_outcome"],
                document["selected_route_status"],
                document["terminal_status"],
                document["occurrence_closure_status"],
                tuple(document["remaining_blockers"]),
                document["official_execution_allowed"],
                document["schema_version"],
            )
        except (TypeError, ValueError) as error:
            if isinstance(error, Phase3EBundleV1Error):
                raise
            raise Phase3EBundleV1Error(
                f"invalid bundle manifest member: {error}"
            ) from error
        if (
            document["phase3e_bundle_manifest_id"]
            != result.phase3e_bundle_manifest_id
        ):
            raise Phase3EBundleV1Error("bundle manifest content ID mismatch")
        return result


@dataclass(frozen=True, slots=True)
class VerifiedH2FailedPrefixBundleV1:
    """Pure-data verification result; no runtime authority object is retained."""

    manifest: Phase3EBundleManifestV1
    request: ModelOnlyExecutionRequestV1
    execution_artifact: ModelOnlyQueryExecutionArtifactV1
    recorded_work: RecordedWorkV1

    def __post_init__(self) -> None:
        if (
            type(self.manifest) is not Phase3EBundleManifestV1
            or type(self.request) is not ModelOnlyExecutionRequestV1
            or type(self.execution_artifact)
            is not ModelOnlyQueryExecutionArtifactV1
            or type(self.recorded_work) is not RecordedWorkV1
        ):
            raise Phase3EBundleV1Error(
                "verified bundle result contains a runtime authority or wrong type"
            )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.verified_h2_failed_prefix_bundle.v1",
            "schema_version": SCHEMA_VERSION,
            "phase3e_bundle_manifest_id": (
                self.manifest.phase3e_bundle_manifest_id
            ),
            "model_only_request_id": self.request.request_id,
            "model_only_execution_id": (
                self.execution_artifact.operational_execution_id
            ),
            "model_only_result_id": (
                self.execution_artifact.model_only_result.result_id
            ),
            "common_prefix_work_vector_id": (
                self.recorded_work.work_vector.work_vector_id
            ),
            "verification_status": VERIFICATION_STATUS,
            "selected_route_status": NOT_RUN,
            "terminal_status": NOT_RUN,
            "occurrence_closure_status": NOT_RUN,
            "remaining_blockers": list(REMAINING_BLOCKERS),
            "official_execution_allowed": False,
        }


def _entry(
    role: Phase3EBundleRoleV1,
    *,
    content_identity: str,
    raw: bytes,
) -> Phase3EBundleEntryV1:
    spec = _ROLE_SPECS[role]
    return Phase3EBundleEntryV1(
        role,
        spec.schema_id,
        spec.domain_tag,
        content_identity,
        spec.relative_path,
        _sha256(raw),
        len(raw),
    )


def _artifact_documents_v1(
    request: ModelOnlyExecutionRequestV1,
    artifact: ModelOnlyQueryExecutionArtifactV1,
) -> tuple[dict[Phase3EBundleRoleV1, dict[str, Any]], dict[Phase3EBundleRoleV1, str]]:
    result = artifact.model_only_result
    work_document = recorded_work_to_dict_v1(
        artifact.recorded_work, expected_scope=ActualWorkScope.COMMON_PREFIX
    )
    documents = {
        Phase3EBundleRoleV1.MODEL_ONLY_REQUEST: request.to_dict(),
        Phase3EBundleRoleV1.MODEL_ONLY_EXECUTION: artifact.to_dict(),
        Phase3EBundleRoleV1.MODEL_ONLY_RESULT: result.to_dict(),
        Phase3EBundleRoleV1.ROUTE_DECISION_CONTEXT: result.route_context.to_dict(),
        Phase3EBundleRoleV1.LOGICAL_OCCURRENCE: result.logical_occurrence.to_dict(),
        Phase3EBundleRoleV1.ROUTE_ATTEMPT: result.route_attempt.to_dict(),
        Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK: work_document,
    }
    identities = {
        Phase3EBundleRoleV1.MODEL_ONLY_REQUEST: request.request_id,
        Phase3EBundleRoleV1.MODEL_ONLY_EXECUTION: artifact.operational_execution_id,
        Phase3EBundleRoleV1.MODEL_ONLY_RESULT: result.result_id,
        Phase3EBundleRoleV1.ROUTE_DECISION_CONTEXT: (
            result.route_context.route_decision_context_id
        ),
        Phase3EBundleRoleV1.LOGICAL_OCCURRENCE: (
            result.logical_occurrence.logical_occurrence_id
        ),
        Phase3EBundleRoleV1.ROUTE_ATTEMPT: result.route_attempt.route_attempt_id,
        Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK: work_document[
            "recorded_work_transport_id"
        ],
    }
    return documents, identities


def _build_manifest_v1(
    request: ModelOnlyExecutionRequestV1,
    artifact: ModelOnlyQueryExecutionArtifactV1,
    entries: tuple[Phase3EBundleEntryV1, ...],
) -> Phase3EBundleManifestV1:
    result = artifact.model_only_result
    lease = request.source_lease
    return Phase3EBundleManifestV1(
        lease.source_bundle_sha256,
        lease.source_manifest_sha256,
        lease.source_lease_id,
        lease.query_key,
        request.request_id,
        artifact.operational_execution_id,
        result.result_id,
        result.route_context.route_decision_context_id,
        result.logical_occurrence.logical_occurrence_id,
        result.route_attempt.route_attempt_id,
        artifact.recorded_work.work_vector.work_vector_id,
        TypedNotApplicable(TERMINAL_NOT_APPLICABLE_REASON),
        TypedNotApplicable(OCCURRENCE_NOT_APPLICABLE_REASON),
        entries,
    )


def write_h2_failed_prefix_bundle_v1(
    output_dir: str | Path,
    *,
    source_bundle: str | Path,
    request: ModelOnlyExecutionRequestV1,
    execution: ModelOnlyQueryExecutionV1,
) -> Phase3EBundleManifestV1:
    """Persist one executor-authenticated H2 prefix as pure canonical bytes."""

    if type(request) is not ModelOnlyExecutionRequestV1:
        raise Phase3EBundleV1Error("bundle writer requires a typed execution request")
    try:
        parent_source = load_phase3c_model_source_v1(
            source_bundle, query_key=LOCAL_QUERY_KEY
        )
        retained = verify_model_only_failed_prefix_execution_v1(execution)
        artifact = verify_model_only_failed_prefix_artifact_v1(
            retained.to_dict(), request=request, source=parent_source
        )
    except ValueError as error:
        raise Phase3EBundleV1Error(
            f"bundle writer requires an authenticated H2 failed prefix: {error}"
        ) from error
    if artifact.request_id != request.request_id:
        raise Phase3EBundleV1Error("execution and bundle request differ")

    root = Path(output_dir)
    if root.exists():
        if root.is_symlink() or not root.is_dir() or any(root.iterdir()):
            raise Phase3EBundleV1Error(
                "bundle output directory must be absent or an empty real directory"
            )
    else:
        root.mkdir(parents=True)
    documents, identities = _artifact_documents_v1(request, artifact)
    raw_by_role = {
        role: canonical_json_bytes(document)
        for role, document in documents.items()
    }
    entries = tuple(
        sorted(
            (
                _entry(role, content_identity=identities[role], raw=raw)
                for role, raw in raw_by_role.items()
            ),
            key=lambda row: row.relative_path,
        )
    )
    manifest = _build_manifest_v1(request, artifact, entries)
    for entry in entries:
        path = root / entry.relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw_by_role[entry.role])
    manifest_raw = canonical_json_bytes(manifest.to_dict())
    (root / MANIFEST_FILENAME).write_bytes(manifest_raw)
    (root / MANIFEST_CHECKSUM_FILENAME).write_text(
        f"{_sha256(manifest_raw)}  {MANIFEST_FILENAME}\n", encoding="ascii"
    )
    return manifest


def _read_regular_file(root: Path, relative_path: str) -> bytes:
    safe = _safe_relative_path(relative_path)
    path = root / safe
    try:
        metadata = path.lstat()
    except OSError as error:
        raise Phase3EBundleV1Error(f"bundle file is missing: {safe}") from error
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise Phase3EBundleV1Error(f"bundle file is not a regular file: {safe}")
    if metadata.st_size > _MAX_DOCUMENT_BYTES:
        raise Phase3EBundleV1Error(f"bundle file exceeds size cap: {safe}")
    return path.read_bytes()


def _verify_bundle_topology(root: Path) -> None:
    expected_files = {
        MANIFEST_FILENAME,
        MANIFEST_CHECKSUM_FILENAME,
        *(spec.relative_path for spec in _ROLE_SPECS.values()),
    }
    observed_files: set[str] = set()
    for directory, dirnames, filenames in os.walk(root, followlinks=False):
        base = Path(directory)
        for dirname in dirnames:
            if (base / dirname).is_symlink():
                raise Phase3EBundleV1Error("bundle directory symlinks are forbidden")
        for filename in filenames:
            path = base / filename
            if path.is_symlink() or not path.is_file():
                raise Phase3EBundleV1Error("bundle contains a non-regular file")
            observed_files.add(path.relative_to(root).as_posix())
    if observed_files != expected_files:
        raise Phase3EBundleV1Error(
            "bundle topology mismatch: "
            f"missing={sorted(expected_files - observed_files)}, "
            f"unexpected={sorted(observed_files - expected_files)}"
        )


def _acquire_bundle_snapshot_v1(root: Path) -> dict[str, bytes]:
    """Retain one complete read-set and reject topology/read instability."""

    _verify_bundle_topology(root)
    paths = (
        MANIFEST_FILENAME,
        MANIFEST_CHECKSUM_FILENAME,
        *(spec.relative_path for spec in _ROLE_SPECS.values()),
    )
    snapshot = {path: _read_regular_file(root, path) for path in paths}
    _verify_bundle_topology(root)
    if any(_read_regular_file(root, path) != raw for path, raw in snapshot.items()):
        raise Phase3EBundleV1Error("bundle changed while acquiring its read-set")
    return snapshot


def _recheck_bundle_snapshot_v1(root: Path, snapshot: Mapping[str, bytes]) -> None:
    _verify_bundle_topology(root)
    if any(_read_regular_file(root, path) != raw for path, raw in snapshot.items()):
        raise Phase3EBundleV1Error("bundle changed during semantic replay")


def verify_h2_failed_prefix_bundle_v1(
    bundle_dir: str | Path,
    *,
    source_bundle: str | Path,
) -> VerifiedH2FailedPrefixBundleV1:
    """Independently replay an H2 failure-prefix bundle without any solver."""

    root = Path(bundle_dir)
    if root.is_symlink() or not root.is_dir():
        raise Phase3EBundleV1Error("bundle root must be a real directory")
    root = root.resolve(strict=True)
    snapshot = _acquire_bundle_snapshot_v1(root)
    manifest_raw = snapshot[MANIFEST_FILENAME]
    checksum_raw = snapshot[MANIFEST_CHECKSUM_FILENAME]
    expected_checksum = f"{_sha256(manifest_raw)}  {MANIFEST_FILENAME}\n".encode(
        "ascii"
    )
    if checksum_raw != expected_checksum:
        raise Phase3EBundleV1Error("manifest checksum file mismatch")
    manifest = Phase3EBundleManifestV1.from_dict(
        _plain_canonical_object(manifest_raw, source=MANIFEST_FILENAME)
    )

    documents: dict[Phase3EBundleRoleV1, dict[str, Any]] = {}
    for entry in manifest.entries:
        raw = snapshot[entry.relative_path]
        if len(raw) != entry.size_bytes or _sha256(raw) != entry.sha256:
            raise Phase3EBundleV1Error(
                f"bundle entry byte digest mismatch: {entry.relative_path}"
            )
        document = _plain_canonical_object(raw, source=entry.relative_path)
        if document.get("schema") != entry.schema_id:
            raise Phase3EBundleV1Error(
                f"bundle entry schema differs from its role: {entry.relative_path}"
            )
        documents[entry.role] = document

    try:
        request = parse_model_only_execution_request_v1(
            documents[Phase3EBundleRoleV1.MODEL_ONLY_REQUEST]
        )
        parent_source = load_phase3c_model_source_v1(
            source_bundle, query_key=LOCAL_QUERY_KEY
        )
        artifact = verify_model_only_failed_prefix_artifact_v1(
            documents[Phase3EBundleRoleV1.MODEL_ONLY_EXECUTION],
            request=request,
            source=parent_source,
        )
        context = RouteDecisionContextV1.from_dict(
            documents[Phase3EBundleRoleV1.ROUTE_DECISION_CONTEXT]
        )
        occurrence = LogicalOccurrenceV1.from_dict(
            documents[Phase3EBundleRoleV1.LOGICAL_OCCURRENCE]
        )
        attempt = RouteAttemptV1.from_dict(
            documents[Phase3EBundleRoleV1.ROUTE_ATTEMPT]
        )
        work = recorded_work_from_dict_v1(
            documents[Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK],
            expected_scope=ActualWorkScope.COMMON_PREFIX,
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, Phase3EBundleV1Error):
            raise
        raise Phase3EBundleV1Error(
            f"bundle semantic replay failed: {error}"
        ) from error

    result = artifact.model_only_result
    if documents[Phase3EBundleRoleV1.MODEL_ONLY_RESULT] != result.to_dict():
        raise Phase3EBundleV1Error(
            "standalone model-only result differs from the execution artifact"
        )
    if (
        context != result.route_context
        or occurrence != result.logical_occurrence
        or attempt != result.route_attempt
        or work != artifact.recorded_work
    ):
        raise Phase3EBundleV1Error(
            "bundle context/occurrence/attempt/work was spliced from another execution"
        )

    work_document = documents[
        Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK
    ]
    actual_ids = {
        Phase3EBundleRoleV1.MODEL_ONLY_REQUEST: request.request_id,
        Phase3EBundleRoleV1.MODEL_ONLY_EXECUTION: artifact.operational_execution_id,
        Phase3EBundleRoleV1.MODEL_ONLY_RESULT: result.result_id,
        Phase3EBundleRoleV1.ROUTE_DECISION_CONTEXT: context.route_decision_context_id,
        Phase3EBundleRoleV1.LOGICAL_OCCURRENCE: occurrence.logical_occurrence_id,
        Phase3EBundleRoleV1.ROUTE_ATTEMPT: attempt.route_attempt_id,
        Phase3EBundleRoleV1.COMMON_PREFIX_RECORDED_WORK: work_document[
            "recorded_work_transport_id"
        ],
    }
    if any(
        entry.content_id != actual_ids[entry.role]
        for entry in manifest.entries
    ):
        raise Phase3EBundleV1Error(
            "bundle entry content ID differs from semantic replay"
        )
    lease = request.source_lease
    expected_manifest_refs = (
        lease.source_bundle_sha256,
        lease.source_manifest_sha256,
        lease.source_lease_id,
        lease.query_key,
        request.request_id,
        artifact.operational_execution_id,
        result.result_id,
        context.route_decision_context_id,
        occurrence.logical_occurrence_id,
        attempt.route_attempt_id,
        work.work_vector.work_vector_id,
    )
    actual_manifest_refs = (
        manifest.source_bundle_sha256,
        manifest.source_manifest_sha256,
        manifest.source_lease_id,
        manifest.query_key,
        manifest.model_only_request_id,
        manifest.model_only_execution_id,
        manifest.model_only_result_id,
        manifest.route_decision_context_id,
        manifest.logical_occurrence_id,
        manifest.route_attempt_id,
        manifest.common_prefix_work_vector_id,
    )
    if actual_manifest_refs != expected_manifest_refs:
        raise Phase3EBundleV1Error("bundle manifest identity chain is stale or spliced")
    _recheck_bundle_snapshot_v1(root, snapshot)
    return VerifiedH2FailedPrefixBundleV1(manifest, request, artifact, work)


__all__ = [
    "BUNDLE_SCOPE",
    "Phase3EBundleEntryV1",
    "Phase3EBundleManifestV1",
    "Phase3EBundleRoleV1",
    "Phase3EBundleV1Error",
    "RECORDED_WORK_TRANSPORT_SCHEMA",
    "REMAINING_BLOCKERS",
    "VERIFICATION_STATUS",
    "VerifiedH2FailedPrefixBundleV1",
    "recorded_work_from_dict_v1",
    "recorded_work_to_dict_v1",
    "recorded_work_transport_id_v1",
    "verify_h2_failed_prefix_bundle_v1",
    "write_h2_failed_prefix_bundle_v1",
]
