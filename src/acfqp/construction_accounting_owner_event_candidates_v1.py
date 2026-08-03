"""Semantic closure for the 71 owner-emittable construction paths.

This authority closes exactly the 89 operation sites registered by the K7
V3 boundary manifest.  It joins the immutable source archive, an exact
five-stage completed event transcript, and the production execution identity.
The result is deliberately a *candidate* layer: it does not mint a
``CounterRecord``, ``WorkVector`` or ``ComparisonVector``.  The remaining
shared-resource and profile-native-zero families must be joined first.

In particular, an absent event becomes an explicit owner-window zero only
after every source site for the path has been found in the frozen source and
the corresponding stage has completed.  A partial/aborted transcript can
never create a zero candidate.
"""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from dataclasses import InitVar, dataclass, field
import hashlib
import importlib.util
import io
from typing import Any, Mapping, NoReturn
import zipfile

from acfqp.accounting_v1 import ReducerEnum
from acfqp import construction_accounting_partial_native_v1 as partial
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_profile_native_zero_rules_v1 as zero_rules
from acfqp import v075_k7_root_cap_operation_boundary_manifest_v3 as boundary_v3
from acfqp.phase3e_ids import (
    CONSTRUCTION_OWNER_BOUNDARY_SITE_CLOSURE_V1_DOMAIN,
    CONSTRUCTION_OWNER_EVENT_CANDIDATE_SET_V1_DOMAIN,
    CONSTRUCTION_OWNER_EVENT_EXECUTION_BINDING_V1_DOMAIN,
    CONSTRUCTION_OWNER_PATH_COUNTER_CANDIDATE_V1_DOMAIN,
    CONSTRUCTION_OWNER_POSTEXEC_BINDING_V1_DOMAIN,
    CONSTRUCTION_OWNER_SOURCE_CODE_IDENTITY_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.23"
PROFILE_KEY = "construction_owner_event_candidates_v1"
EXPECTED_SITE_COUNT = 89
EXPECTED_PATH_COUNT = 71
EXPECTED_SOURCE_HOOK_COUNT = 59
EXPECTED_SOURCE_HOOK_KEY_COUNT = 54
_DUPLICATED_SOURCE_HOOKS = frozenset(
    {
        (
            "acfqp.sequential_bernoulli_acquisition_v1",
            "_outer_confidence_bounds_accounted_v2",
            "sequential.confidence.cache.hit",
        ),
        (
            "acfqp.sequential_bernoulli_acquisition_v1",
            "_outer_confidence_bounds_accounted_v2",
            "sequential.confidence.cache.miss",
        ),
        (
            "acfqp.v075_batch_native_planning_backend_v2",
            "_compile_quotient",
            "batch-planning.quotient-cell.compile",
        ),
        (
            "acfqp.v075_batch_native_planning_backend_v2",
            "_options",
            "batch-planning.semantic-option.compile",
        ),
        (
            "acfqp.v075_batch_native_planning_backend_v2",
            "_options",
            "batch-planning.concretizer-ground-action.bind",
        ),
    }
)
_CONTROL_SOURCE_MODULES = (
    "acfqp.construction_accounting_owned_runtime_v1",
    "acfqp.construction_accounting_partial_native_v1",
    "acfqp.v075_k7_broker_business_process_entry_v2",
    "acfqp.v075_k7_broker_worker_process_entry_v2",
    "acfqp.v075_k7_production_role_sandbox_v2",
    "acfqp.v075_k7_root_cap_operation_boundary_manifest_v3",
    "acfqp.v075_k7_root_cap_owned_partial_runner_v1",
)

SITE_CLOSURE_DOMAIN = CONSTRUCTION_OWNER_BOUNDARY_SITE_CLOSURE_V1_DOMAIN
PATH_CANDIDATE_DOMAIN = CONSTRUCTION_OWNER_PATH_COUNTER_CANDIDATE_V1_DOMAIN
CANDIDATE_SET_DOMAIN = CONSTRUCTION_OWNER_EVENT_CANDIDATE_SET_V1_DOMAIN
EXECUTION_BINDING_DOMAIN = CONSTRUCTION_OWNER_EVENT_EXECUTION_BINDING_V1_DOMAIN
SOURCE_CODE_DOMAIN = CONSTRUCTION_OWNER_SOURCE_CODE_IDENTITY_V1_DOMAIN
POSTEXEC_BINDING_DOMAIN = CONSTRUCTION_OWNER_POSTEXEC_BINDING_V1_DOMAIN

POSITIVE_KIND = "POSITIVE_ORDERED_EVENT_STREAM"
ZERO_KIND = "EXPLICIT_OWNER_WINDOW_ZERO"
POSTEXEC_KIND = "DERIVED_EXACT_BOOTSTRAP_CONTROL_FLOW_AND_ZERO_EXIT"

_BINDING_ISSUER = object()
_SITE_ISSUER = object()
_PATH_ISSUER = object()
_SET_ISSUER = object()


class ConstructionAccountingOwnerEventCandidatesV1Error(RuntimeError):
    """The owner-event semantic closure failed closed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionAccountingOwnerEventCandidatesV1Error(message)


def _sha(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionAccountingOwnerEventCandidatesV1Error(
            f"{label} must be one exact SHA-256 identity"
        ) from error


def _local_id(domain: str, payload: Mapping[str, Any]) -> str:
    return content_id(domain, dict(payload))


def _exact_dict(value: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(value) is not dict or set(value) != fields:
        _fail(f"{label} field set changed")
    return value


def _emittable_boundaries() -> tuple[Any, ...]:
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    result = tuple(
        row
        for row in manifest.boundaries
        if row.to_document()["emittable_in_this_fixture"] is True
    )
    if (
        len(result) != EXPECTED_SITE_COUNT
        or len({row.target_path for row in result}) != EXPECTED_PATH_COUNT
    ):
        _fail("official owner-emittable boundary cardinality changed")
    return result


@dataclass(frozen=True, slots=True)
class OwnerEventExecutionBindingV1:
    """Exact identities already verified before semantic site closure.

    ``postexec_attestation_exported`` is intentionally false.  V2 does not
    serialize the process-local sandbox attestation.  The weaker but honest
    binding used here is derived from exact bootstrap/source identities, the
    fixed bootstrap control flow, and both directly reaped zero exits.
    """

    _issuer: InitVar[object]
    request_id: str
    route_identity_id: str
    scientific_occurrence_id: str
    phase3e_logical_occurrence_id: str
    production_role_manifest_id: str
    production_runtime_envelope_id: str
    broker_transcript_id: str
    business_bundle_id: str
    source_snapshot_id: str
    source_archive_sha256: str
    source_archive_byte_count: int
    postexec_binding_id: str
    postexec_binding_kind: str = POSTEXEC_KIND
    postexec_attestation_exported: bool = False
    two_direct_roles_zero_exit: bool = True
    clone_and_thread_creation_denied_by_exact_bootstrap: bool = True

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _BINDING_ISSUER:
            _fail("owner-event execution binding is caller-minted")
        for name in (
            "request_id",
            "route_identity_id",
            "scientific_occurrence_id",
            "phase3e_logical_occurrence_id",
            "production_role_manifest_id",
            "production_runtime_envelope_id",
            "broker_transcript_id",
            "business_bundle_id",
            "source_snapshot_id",
            "source_archive_sha256",
            "postexec_binding_id",
        ):
            _sha(getattr(self, name), name)
        if (
            type(self.source_archive_byte_count) is not int
            or self.source_archive_byte_count <= 0
            or self.postexec_binding_kind != POSTEXEC_KIND
            or self.postexec_attestation_exported is not False
            or self.two_direct_roles_zero_exit is not True
            or self.clone_and_thread_creation_denied_by_exact_bootstrap is not True
        ):
            _fail("owner-event execution binding facts changed")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_event_execution_binding.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "request_id": self.request_id,
            "route_identity_id": self.route_identity_id,
            "scientific_occurrence_id": self.scientific_occurrence_id,
            "phase3e_logical_occurrence_id": self.phase3e_logical_occurrence_id,
            "production_role_manifest_id": self.production_role_manifest_id,
            "production_runtime_envelope_id": self.production_runtime_envelope_id,
            "broker_transcript_id": self.broker_transcript_id,
            "business_bundle_id": self.business_bundle_id,
            "source_snapshot_id": self.source_snapshot_id,
            "source_archive_sha256": self.source_archive_sha256,
            "source_archive_byte_count": self.source_archive_byte_count,
            "postexec_binding_id": self.postexec_binding_id,
            "postexec_binding_kind": self.postexec_binding_kind,
            "postexec_attestation_exported": self.postexec_attestation_exported,
            "two_direct_roles_zero_exit": self.two_direct_roles_zero_exit,
            "clone_and_thread_creation_denied_by_exact_bootstrap": (
                self.clone_and_thread_creation_denied_by_exact_bootstrap
            ),
            "process_local_installation_claimed_directly": False,
            "central_domain_registration_pending": False,
        }

    @property
    def binding_id(self) -> str:
        return _local_id(EXECUTION_BINDING_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owner_event_execution_binding_id": self.binding_id}


@dataclass(frozen=True, slots=True)
class OwnerBoundarySiteClosureV1:
    _issuer: InitVar[object]
    execution_binding_id: str
    partial_native_transcript_id: str
    boundary_id: str
    boundary_key: str
    dispatch_key: str
    stage: str
    path: str
    operation_source_module: str
    operation_source_symbol: str
    source_member_sha256: str
    source_member_byte_count: int
    source_symbol_code_identity_id: str
    stage_start_id: str
    stage_completion_id: str
    ordered_event_ids: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _SITE_ISSUER:
            _fail("owner site closure is caller-minted")
        for name in (
            "execution_binding_id",
            "partial_native_transcript_id",
            "boundary_id",
            "source_member_sha256",
            "source_symbol_code_identity_id",
            "stage_start_id",
            "stage_completion_id",
        ):
            _sha(getattr(self, name), name)
        if (
            type(self.source_member_byte_count) is not int
            or self.source_member_byte_count <= 0
            or type(self.ordered_event_ids) is not tuple
            or len(set(self.ordered_event_ids)) != len(self.ordered_event_ids)
        ):
            _fail("owner site closure shape changed")
        for value in self.ordered_event_ids:
            _sha(value, "site event")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_boundary_site_closure.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_binding_id": self.execution_binding_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "boundary_id": self.boundary_id,
            "boundary_key": self.boundary_key,
            "dispatch_key": self.dispatch_key,
            "stage": self.stage,
            "path": self.path,
            "operation_source_module": self.operation_source_module,
            "operation_source_symbol": self.operation_source_symbol,
            "source_member_sha256": self.source_member_sha256,
            "source_member_byte_count": self.source_member_byte_count,
            "source_symbol_code_identity_id": self.source_symbol_code_identity_id,
            "stage_start_id": self.stage_start_id,
            "stage_completion_id": self.stage_completion_id,
            "ordered_event_ids": list(self.ordered_event_ids),
            "active_stage_binding_verified": True,
            "direct_caller_owner_binding_verified_by_runtime": True,
            "loaded_module_bytes_verified": True,
            "runtime_event_transcript_verified": True,
            "source_symbol_code_identity_verified": True,
            "complete_owner_window": True,
        }

    @property
    def site_closure_id(self) -> str:
        return _local_id(SITE_CLOSURE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owner_boundary_site_closure_id": self.site_closure_id}


@dataclass(frozen=True, slots=True)
class OwnerPathCounterCandidateV1:
    _issuer: InitVar[object]
    execution_binding_id: str
    partial_native_transcript_id: str
    path: str
    semantics_id: str
    owner: str
    unit: str
    lane: str
    scope: str
    reducer: str
    comparison_axis: str | None
    evidence_kind: str
    value: int
    site_closure_ids: tuple[str, ...]
    ordered_event_ids: tuple[str, ...]

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PATH_ISSUER:
            _fail("owner path candidate is caller-minted")
        _sha(self.execution_binding_id, "execution binding")
        _sha(self.partial_native_transcript_id, "partial transcript")
        if (
            self.evidence_kind not in {POSITIVE_KIND, ZERO_KIND}
            or type(self.value) is not int
            or self.value < 0
            or self.reducer != ReducerEnum.SUM.value
            or type(self.site_closure_ids) is not tuple
            or not self.site_closure_ids
            or len(set(self.site_closure_ids)) != len(self.site_closure_ids)
            or type(self.ordered_event_ids) is not tuple
            or len(set(self.ordered_event_ids)) != len(self.ordered_event_ids)
            or self.value != len(self.ordered_event_ids)
            or (self.value == 0) != (self.evidence_kind == ZERO_KIND)
        ):
            _fail("owner path candidate is internally inconsistent")
        for value in (*self.site_closure_ids, *self.ordered_event_ids):
            _sha(value, "path evidence identity")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_path_counter_candidate.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_binding_id": self.execution_binding_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "path": self.path,
            "semantics_id": self.semantics_id,
            "owner": self.owner,
            "unit": self.unit,
            "lane": self.lane,
            "scope": self.scope,
            "reducer": self.reducer,
            "comparison_axis": self.comparison_axis,
            "evidence_kind": self.evidence_kind,
            "value": self.value,
            "site_closure_ids": list(self.site_closure_ids),
            "ordered_event_ids": list(self.ordered_event_ids),
            "observed": True,
            "formal_counter_record": False,
            "native_zero_attestation": False,
            "owner_window_zero_only": self.evidence_kind == ZERO_KIND,
        }

    @property
    def candidate_id(self) -> str:
        return _local_id(PATH_CANDIDATE_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "owner_path_counter_candidate_id": self.candidate_id}


@dataclass(frozen=True, slots=True)
class OwnerEventCandidateSetV1:
    _issuer: InitVar[object]
    execution_binding: OwnerEventExecutionBindingV1 = field(repr=False)
    partial_native_transcript_id: str
    partial_native_terminal_id: str
    site_closures: tuple[OwnerBoundarySiteClosureV1, ...]
    path_candidates: tuple[OwnerPathCounterCandidateV1, ...]

    def __post_init__(self, _issuer: object) -> None:
        if (
            _issuer is not _SET_ISSUER
            or type(self.execution_binding) is not OwnerEventExecutionBindingV1
            or type(self.site_closures) is not tuple
            or type(self.path_candidates) is not tuple
            or len(self.site_closures) != EXPECTED_SITE_COUNT
            or len(self.path_candidates) != EXPECTED_PATH_COUNT
            or tuple(row.boundary_key for row in self.site_closures)
            != tuple(sorted(row.boundary_key for row in self.site_closures))
            or tuple(row.path for row in self.path_candidates)
            != tuple(sorted(row.path for row in self.path_candidates))
            or len({row.site_closure_id for row in self.site_closures})
            != EXPECTED_SITE_COUNT
            or len({row.candidate_id for row in self.path_candidates})
            != EXPECTED_PATH_COUNT
        ):
            _fail("owner event candidate set shape changed")
        _sha(self.partial_native_transcript_id, "partial transcript")
        _sha(self.partial_native_terminal_id, "partial terminal")

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_owner_event_candidate_set.v1",
            "schema_version": SCHEMA_VERSION,
            "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
            "profile_key": PROFILE_KEY,
            "execution_binding_id": self.execution_binding.binding_id,
            "partial_native_transcript_id": self.partial_native_transcript_id,
            "partial_native_terminal_id": self.partial_native_terminal_id,
            "site_closure_ids": [row.site_closure_id for row in self.site_closures],
            "path_candidate_ids": [row.candidate_id for row in self.path_candidates],
            "owner_emittable_site_count": EXPECTED_SITE_COUNT,
            "owner_emittable_path_count": EXPECTED_PATH_COUNT,
            "semantic_owner_event_closure_complete": True,
            "counter_records_materialized": False,
            "work_vector_materialized": False,
            "comparison_vector_materialized": False,
            "shared_resource_paths_joined": False,
            "profile_native_zero_paths_joined": False,
            "derived_paths_joined": False,
            "formal_materialization_allowed": False,
            "official_execution_allowed": False,
            "independent_verifier_pending": True,
            "central_domain_registration_pending": False,
        }

    @property
    def candidate_set_id(self) -> str:
        return _local_id(CANDIDATE_SET_DOMAIN, self._payload())

    def to_document(self) -> dict[str, Any]:
        payload = self._payload()
        return {
            **payload,
            "owner_event_candidate_set_id": _local_id(CANDIDATE_SET_DOMAIN, payload),
        }


_START_FIELDS = {
    "schema", "schema_version", "occurrence_id", "counter_registry_id",
    "stage_profile_id", "boundary_profile_id", "recorder_id", "stage_plan",
    "predecessor_chain_id", "chain_sequence", "coverage_state",
    "occurrence_start_id",
}
_NODE_FIELDS = {
    "acfqp.construction_partial_native_stage_start.v1": {
        "schema", "schema_version", "occurrence_start_id", "occurrence_id",
        "counter_registry_id", "stage_profile_id", "boundary_profile_id",
        "chain_sequence", "predecessor_chain_id", "stage_index", "stage_kind",
        "stage_start_id",
    },
    "acfqp.construction_partial_native_operation_event.v1": {
        "schema", "schema_version", "occurrence_start_id", "occurrence_id",
        "counter_registry_id", "stage_profile_id", "boundary_profile_id",
        "chain_sequence", "predecessor_chain_id", "stage_index", "stage_kind",
        "stage_event_sequence", "site_id", "path", "reducer", "amount",
        "operation_event_id",
    },
    "acfqp.construction_partial_native_stage_completion.v1": {
        "schema", "schema_version", "occurrence_start_id", "occurrence_id",
        "counter_registry_id", "stage_profile_id", "boundary_profile_id",
        "chain_sequence", "predecessor_chain_id", "stage_index", "stage_kind",
        "stage_event_count", "total_event_count", "output_bindings",
        "stage_completion_id",
    },
    "acfqp.construction_partial_native_occurrence_completion.v1": {
        "schema", "schema_version", "occurrence_start_id", "occurrence_id",
        "counter_registry_id", "stage_profile_id", "boundary_profile_id",
        "chain_sequence", "predecessor_chain_id", "completed_stage_count",
        "total_event_count", "emitted_event_ids", "occurrence_completion_id",
    },
    "acfqp.construction_partial_native_occurrence_abort.v1": {
        "schema", "schema_version", "occurrence_start_id", "occurrence_id",
        "counter_registry_id", "stage_profile_id", "boundary_profile_id",
        "chain_sequence", "predecessor_chain_id", "completed_stage_count",
        "total_event_count", "emitted_event_ids", "aborted_stage_index",
        "aborted_stage_kind", "exception_module", "exception_qualname", "reason",
        "occurrence_abort_id",
    },
}
_TRANSCRIPT_FIELDS = {
    "schema", "schema_version", "occurrence_start", "chain_nodes",
    "terminal_kind", "occurrence_completion_id", "occurrence_abort_id",
    "counter_records", "work_vector", "comparison_vector", "actual_projection",
    "coverage_state", "absent_native_events_inferred_zero",
    "official_execution_allowed", "partial_native_transcript_id",
}


def _typed_null(document: Any) -> partial.PartialNativeNotApplicableV1:
    value = _exact_dict(document, {"kind", "reason"}, "typed null")
    return partial.PartialNativeNotApplicableV1(value["reason"], value["kind"])


def _decode_transcript(document: Any) -> partial.PartialNativeOccurrenceTranscriptV1:
    doc = _exact_dict(document, _TRANSCRIPT_FIELDS, "partial transcript")
    if doc["terminal_kind"] != "COMPLETED":
        _fail("owner-window closure requires a completed five-stage transcript")
    start_doc = _exact_dict(doc["occurrence_start"], _START_FIELDS, "occurrence start")
    start = partial.PartialNativeOccurrenceStartV1(
        occurrence_id=start_doc["occurrence_id"],
        counter_registry_id=start_doc["counter_registry_id"],
        stage_profile_id=start_doc["stage_profile_id"],
        boundary_profile_id=start_doc["boundary_profile_id"],
        recorder_id=start_doc["recorder_id"],
        stage_plan=tuple(start_doc["stage_plan"]),
        predecessor_chain_id=_typed_null(start_doc["predecessor_chain_id"]),
        chain_sequence=start_doc["chain_sequence"],
    )
    if start.start_id != start_doc["occurrence_start_id"]:
        _fail("occurrence-start content identity changed")
    nodes: list[Any] = []
    for raw in doc["chain_nodes"]:
        if type(raw) is not dict or raw.get("schema") not in _NODE_FIELDS:
            _fail("partial transcript contains an unknown node schema")
        row = _exact_dict(raw, _NODE_FIELDS[raw["schema"]], "partial chain node")
        common = {
            name: row[name]
            for name in (
                "occurrence_start_id", "occurrence_id", "counter_registry_id",
                "stage_profile_id", "boundary_profile_id", "chain_sequence",
                "predecessor_chain_id",
            )
        }
        schema = row["schema"]
        if schema.endswith("stage_start.v1"):
            node = partial.PartialNativeStageStartV1(
                **common, stage_index=row["stage_index"], stage_kind=row["stage_kind"]
            )
            claimed = row["stage_start_id"]
        elif schema.endswith("operation_event.v1"):
            node = partial.PartialNativeOperationEventV1(
                **common,
                stage_index=row["stage_index"], stage_kind=row["stage_kind"],
                stage_event_sequence=row["stage_event_sequence"], site_id=row["site_id"],
                path=row["path"], reducer=row["reducer"], amount=row["amount"],
            )
            claimed = row["operation_event_id"]
        elif schema.endswith("stage_completion.v1"):
            outputs = tuple(
                partial.PartialNativeOutputBindingV1(
                    **_exact_dict(value, {"role", "artifact_id"}, "output binding")
                )
                for value in row["output_bindings"]
            )
            node = partial.PartialNativeStageCompletionV1(
                **common,
                stage_index=row["stage_index"], stage_kind=row["stage_kind"],
                stage_event_count=row["stage_event_count"],
                total_event_count=row["total_event_count"], output_bindings=outputs,
            )
            claimed = row["stage_completion_id"]
        elif schema.endswith("occurrence_completion.v1"):
            node = partial.PartialNativeOccurrenceCompletionV1(
                **common, completed_stage_count=row["completed_stage_count"],
                total_event_count=row["total_event_count"],
                emitted_event_ids=tuple(row["emitted_event_ids"]),
            )
            claimed = row["occurrence_completion_id"]
        else:
            def ref(value: Any) -> Any:
                return _typed_null(value) if type(value) is dict else value
            node = partial.PartialNativeOccurrenceAbortV1(
                **common, completed_stage_count=row["completed_stage_count"],
                total_event_count=row["total_event_count"],
                emitted_event_ids=tuple(row["emitted_event_ids"]),
                aborted_stage_index=ref(row["aborted_stage_index"]),
                aborted_stage_kind=ref(row["aborted_stage_kind"]),
                exception_module=ref(row["exception_module"]),
                exception_qualname=ref(row["exception_qualname"]), reason=row["reason"],
            )
            claimed = row["occurrence_abort_id"]
        if node.chain_id != claimed:
            _fail("partial chain node content identity changed")
        nodes.append(node)
    transcript = partial.PartialNativeOccurrenceTranscriptV1(start, tuple(nodes))
    partial.verify_partial_native_occurrence_transcript_v1(transcript)
    if transcript.transcript_id != doc["partial_native_transcript_id"]:
        _fail("partial transcript content identity changed")
    return transcript


class _HookVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self._qualname: list[str] = []
        self.hooks: list[tuple[str, str]] = []
        self.symbol_nodes: dict[str, ast.AST] = {}

    def visit_ClassDef(self, node: ast.ClassDef) -> None:  # noqa: N802
        self._qualname.append(node.name)
        self.symbol_nodes[".".join(self._qualname)] = node
        self.generic_visit(node)
        self._qualname.pop()

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self._qualname.append(node.name)
        self.symbol_nodes[".".join(self._qualname)] = node
        self.generic_visit(node)
        self._qualname.pop()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self._visit_function(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "emit_owned_operation_v1"
            and len(node.args) >= 1
            and isinstance(node.args[0], ast.Constant)
            and type(node.args[0].value) is str
        ):
            self.hooks.append((".".join(self._qualname), node.args[0].value))
        self.generic_visit(node)


def _module_member(module_name: str) -> str:
    return module_name.replace(".", "/") + ".py"


def _archive_sources(raw: bytes, binding: OwnerEventExecutionBindingV1) -> dict[str, bytes]:
    if (
        type(raw) is not bytes
        or hashlib.sha256(raw).hexdigest() != binding.source_archive_sha256
        or len(raw) != binding.source_archive_byte_count
    ):
        _fail("source archive bytes differ from the execution binding")
    result: dict[str, bytes] = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw), "r") as handle:
            infos = handle.infolist()
            if len({row.filename for row in infos}) != len(infos):
                _fail("source archive repeats a member")
            for info in infos:
                if (
                    info.compress_type != zipfile.ZIP_STORED
                    or info.date_time != (1980, 1, 1, 0, 0, 0)
                    or info.filename.startswith("/")
                    or ".." in info.filename.split("/")
                ):
                    _fail("source archive member metadata is noncanonical")
                result[info.filename] = handle.read(info)
    except (OSError, zipfile.BadZipFile, RuntimeError) as error:
        raise ConstructionAccountingOwnerEventCandidatesV1Error(
            "source archive is not a readable deterministic ZIP"
        ) from error
    return result


def _live_source_bytes(module_name: str) -> bytes:
    spec = importlib.util.find_spec(module_name)
    if spec is None or type(spec.origin) is not str or spec.loader is None:
        _fail(f"loaded source authority is unavailable for {module_name}")
    loader = spec.loader
    getter = getattr(loader, "get_data", None)
    try:
        raw = getter(spec.origin) if getter is not None else None
    except OSError as error:
        raise ConstructionAccountingOwnerEventCandidatesV1Error(
            f"loaded source bytes are unavailable for {module_name}"
        ) from error
    if type(raw) is not bytes or not raw:
        _fail(f"loaded source bytes are unavailable for {module_name}")
    return raw


def _source_closure(
    *, archive_raw: bytes, binding: OwnerEventExecutionBindingV1
) -> dict[str, tuple[str, int, _HookVisitor]]:
    boundaries = _emittable_boundaries()
    modules = tuple(sorted({row.operation_source_module for row in boundaries}))
    members = _archive_sources(archive_raw, binding)
    result: dict[str, tuple[str, int, _HookVisitor]] = {}
    observed: Counter[tuple[str, str, str]] = Counter()
    for module_name in modules:
        member = _module_member(module_name)
        if member not in members:
            _fail(f"source archive omitted owner module {module_name}")
        raw = members[member]
        if raw != _live_source_bytes(module_name):
            _fail(f"archive and loaded source bytes differ for {module_name}")
        try:
            tree = ast.parse(raw, filename=member)
        except (SyntaxError, ValueError) as error:
            raise ConstructionAccountingOwnerEventCandidatesV1Error(
                f"owner source cannot be parsed: {module_name}"
            ) from error
        visitor = _HookVisitor()
        visitor.visit(tree)
        for symbol, dispatch in visitor.hooks:
            observed[(module_name, symbol, dispatch)] += 1
        result[module_name] = (hashlib.sha256(raw).hexdigest(), len(raw), visitor)

    # The archive identity must also bind the authority which disables the
    # low-level test API and the entry/bootstrap hand-off which consumes the
    # one-shot postexec attestation.  These are execution-control sources, not
    # additional owner sites, so they do not enter the 89-site result.
    control_trees: dict[str, ast.Module] = {}
    for module_name in _CONTROL_SOURCE_MODULES:
        member = _module_member(module_name)
        if member not in members:
            _fail(f"source archive omitted accounting control module {module_name}")
        raw = members[member]
        if raw != _live_source_bytes(module_name):
            _fail(f"archive and loaded source bytes differ for {module_name}")
        try:
            control_trees[module_name] = ast.parse(raw, filename=member)
        except (SyntaxError, ValueError) as error:
            raise ConstructionAccountingOwnerEventCandidatesV1Error(
                f"accounting control source cannot be parsed: {module_name}"
            ) from error

    runner_tree = control_trees[
        "acfqp.v075_k7_root_cap_owned_partial_runner_v1"
    ]
    activations = [
        node
        for node in ast.walk(runner_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "activate_owned_construction_accounting_v1"
    ]
    if (
        len(activations) != 1
        or any(
            keyword.arg == "_allow_low_level_test_api"
            for keyword in activations[0].keywords
        )
    ):
        _fail("production owned runner no-test-API activation changed")
    for module_name in (
        "acfqp.v075_k7_broker_business_process_entry_v2",
        "acfqp.v075_k7_broker_worker_process_entry_v2",
    ):
        consumptions = [
            node
            for node in ast.walk(control_trees[module_name])
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr
            == "consume_v075_k7_production_role_postexec_entry_attestation_v2"
        ]
        if len(consumptions) != 1:
            _fail("production role one-shot postexec consumption changed")
    expected = Counter(
        (
            row.operation_source_module,
            row.operation_source_symbol,
            row.dispatch_key,
        )
        for row in boundaries
    )
    # One source hook can serve the same semantic site in initial and closure
    # stages.  The manifest counter is therefore collapsed to one required
    # expression per owner/symbol/dispatch triple.
    expected = Counter(
        {key: 2 if key in _DUPLICATED_SOURCE_HOOKS else 1 for key in expected}
    )
    if (
        observed != expected
        or sum(observed.values()) != EXPECTED_SOURCE_HOOK_COUNT
        or len(observed) != EXPECTED_SOURCE_HOOK_KEY_COUNT
    ):
        _fail("owner source hook inventory differs from the exact V3 manifest")
    return result


def _derive_from_verified_inputs(
    *,
    execution_binding: OwnerEventExecutionBindingV1,
    source_archive_raw: bytes,
    transcript_document: Mapping[str, Any],
) -> OwnerEventCandidateSetV1:
    if type(execution_binding) is not OwnerEventExecutionBindingV1:
        _fail("candidate derivation requires one exact execution binding")
    transcript = _decode_transcript(dict(transcript_document))
    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    manifest = boundary_v3.official_k7_root_cap_operation_boundary_manifest_v3()
    coverage = zero_rules.official_owner_boundary_coverage_profile_v1()
    if (
        transcript.start.occurrence_id != execution_binding.scientific_occurrence_id
        or transcript.start.counter_registry_id != registry.registry_id
        or transcript.start.stage_profile_id != stage_profile.stage_profile_id
        or transcript.start.boundary_profile_id != manifest.manifest_id
        or coverage.counter_registry_id != registry.registry_id
        or coverage.boundary_manifest_id != manifest.manifest_id
    ):
        _fail("transcript crossed its occurrence or V3/V6 authority chain")
    sources = _source_closure(
        archive_raw=source_archive_raw, binding=execution_binding
    )
    starts: dict[str, Any] = {}
    completions: dict[str, Any] = {}
    events: list[Any] = []
    for node in transcript.nodes:
        if type(node) is partial.PartialNativeStageStartV1:
            starts[node.stage_kind.value] = node
        elif type(node) is partial.PartialNativeStageCompletionV1:
            completions[node.stage_kind.value] = node
        elif type(node) is partial.PartialNativeOperationEventV1:
            if node.amount != 1:
                _fail("owner production events must be exact unit primitives")
            events.append(node)
    expected_stages = {item.value for item in partial.ROOT_CAP_FIVE_STAGE_PLAN_V1}
    if set(starts) != expected_stages or set(completions) != expected_stages:
        _fail("owner transcript lacks a complete five-stage window")
    by_site_events: dict[str, list[Any]] = defaultdict(list)
    boundary_by_key = {
        row.boundary_key: row for row in _emittable_boundaries()
    }
    for event in events:
        row = boundary_by_key.get(event.site_id)
        if (
            row is None
            or row.target_path != event.path
            or row.stage.value != event.stage_kind.value
            or row.reducer is not event.reducer
        ):
            _fail("runtime event crossed its exact site/path/stage binding")
        by_site_events[event.site_id].append(event)
    site_closures: list[OwnerBoundarySiteClosureV1] = []
    for row in sorted(boundary_by_key.values(), key=lambda item: item.boundary_key):
        digest, byte_count, visitor = sources[row.operation_source_module]
        symbol_node = visitor.symbol_nodes.get(row.operation_source_symbol)
        if symbol_node is None:
            _fail("registered owner source symbol is absent from the archive")
        code_payload = {
            "source_snapshot_id": execution_binding.source_snapshot_id,
            "module": row.operation_source_module,
            "source_member_sha256": digest,
            "symbol": row.operation_source_symbol,
            "symbol_ast_sha256": hashlib.sha256(
                ast.dump(symbol_node, include_attributes=False).encode("utf-8")
            ).hexdigest(),
        }
        code_id = _local_id(SOURCE_CODE_DOMAIN, code_payload)
        stage_start = starts[row.stage.value]
        stage_completion = completions[row.stage.value]
        site_closures.append(
            OwnerBoundarySiteClosureV1(
                _SITE_ISSUER,
                execution_binding.binding_id,
                transcript.transcript_id,
                row.boundary_id,
                row.boundary_key,
                row.dispatch_key,
                row.stage.value,
                row.target_path,
                row.operation_source_module,
                row.operation_source_symbol,
                digest,
                byte_count,
                code_id,
                stage_start.chain_id,
                stage_completion.chain_id,
                tuple(event.event_id for event in by_site_events[row.boundary_key]),
            )
        )
    closures_by_path: dict[str, list[OwnerBoundarySiteClosureV1]] = defaultdict(list)
    for closure in site_closures:
        closures_by_path[closure.path].append(closure)
    event_order = {event.event_id: index for index, event in enumerate(events)}
    candidates: list[OwnerPathCounterCandidateV1] = []
    for path in sorted(closures_by_path):
        leaf = registry.by_path[path]
        closures = closures_by_path[path]
        event_ids = tuple(
            sorted(
                (event_id for closure in closures for event_id in closure.ordered_event_ids),
                key=event_order.__getitem__,
            )
        )
        candidates.append(
            OwnerPathCounterCandidateV1(
                _PATH_ISSUER,
                execution_binding.binding_id,
                transcript.transcript_id,
                path,
                leaf.semantics_id,
                leaf.owner,
                leaf.unit,
                leaf.lane.value,
                leaf.scope,
                leaf.reducer.value,
                leaf.comparison_axis,
                POSITIVE_KIND if event_ids else ZERO_KIND,
                len(event_ids),
                tuple(closure.site_closure_id for closure in closures),
                event_ids,
            )
        )
    terminal = transcript.nodes[-1]
    result = OwnerEventCandidateSetV1(
        _SET_ISSUER,
        execution_binding,
        transcript.transcript_id,
        terminal.chain_id,
        tuple(site_closures),
        tuple(candidates),
    )
    verify_owner_event_candidate_set_v1(result)
    return result


def _derive_v075_k7_owner_event_candidates_from_verified_bundle_v1(
    *,
    role_manifest: Any,
    runtime_envelope: Any,
    request_replay: Any,
    verified_business_bundle: Any,
) -> OwnerEventCandidateSetV1:
    """Derive candidates from a bundle validated in the current call frame.

    This private boundary never accepts raw bytes or caller-minted facts.  The
    public entry point below remains the independent raw-byte verifier; trusted
    aggregate validation may reuse its issuer-owned bundle only within the
    same complete validation frame.
    """

    from acfqp import v075_k7_child_business_bundle_v1 as business_v1
    from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
    from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
    from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1

    if (
        type(role_manifest) is not manifest_v2.K7ProductionRoleManifestV2
        or type(runtime_envelope) is not runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2
        or type(request_replay) is not replay_v1.V075K7SuccessorPortableRequestReplayV1
        or type(verified_business_bundle)
        is not business_v1.V075K7ChildBusinessBundleV1
    ):
        _fail("production owner-event join received a foreign artifact")
    role_manifest.assert_current()
    request = request_replay.request
    business_bundle_raw = verified_business_bundle.canonical_bytes
    bundle_doc = verified_business_bundle.to_document()
    actual_request_facts = tuple(
        bundle_doc[field]
        for field in business_v1._BUNDLE_VALIDATION_FACT_FIELDS[1:]  # noqa: SLF001
    )
    if (
        role_manifest.request.canonical_bytes != request.canonical_bytes
        or actual_request_facts
        != business_v1._request_identity_primitives_v1(request_replay)  # noqa: SLF001
    ):
        _fail("verified business bundle crossed its exact manifest request")
    accounted = request.profile.accounted_profile
    transport = accounted.transport_profile
    archive_raw = transport._archive_bytes  # noqa: SLF001
    bundle_id = verified_business_bundle.bundle_id
    if (
        runtime_envelope.manifest_id != role_manifest.manifest_id
        or runtime_envelope.binding.request_id != request.request_id
        or runtime_envelope.binding.route_identity_id
        != request.route_identity.route_identity_id
        or runtime_envelope.business_result_id != bundle_id
        or runtime_envelope.business_result_sha256
        != hashlib.sha256(business_bundle_raw).hexdigest()
        or runtime_envelope.business_result_byte_count != len(business_bundle_raw)
    ):
        _fail("production manifest/runtime/business identity graph crossed")
    postexec_payload = {
        "production_role_manifest_id": role_manifest.manifest_id,
        "production_runtime_envelope_id": runtime_envelope.envelope_id,
        "worker_bootstrap_sha256": role_manifest.worker_role.to_document()[
            "bootstrap_sha256"
        ],
        "business_bootstrap_sha256": role_manifest.business_role.to_document()[
            "bootstrap_sha256"
        ],
        "worker_entry_source_sha256": role_manifest.worker_role.entry_source_sha256,
        "business_entry_source_sha256": role_manifest.business_role.entry_source_sha256,
        "role_exit_codes": [row["exit_code"] for row in runtime_envelope.role_rows],
        "direct_pidfd_reaped": [
            row["direct_pidfd_reaped"] for row in runtime_envelope.role_rows
        ],
        "postexec_attestation_exported": False,
        "derivation_kind": POSTEXEC_KIND,
    }
    binding = OwnerEventExecutionBindingV1(
        _BINDING_ISSUER,
        request.request_id,
        request.route_identity.route_identity_id,
        request.scientific_occurrence_id,
        request.occurrence_mapping.phase3e_logical_occurrence_id,
        role_manifest.manifest_id,
        runtime_envelope.envelope_id,
        runtime_envelope.transcript.transcript_id,
        bundle_id,
        role_manifest.source_snapshot_id,
        role_manifest.source_archive_sha256,
        role_manifest.source_archive_byte_count,
        _local_id(POSTEXEC_BINDING_DOMAIN, postexec_payload),
    )
    return _derive_from_verified_inputs(
        execution_binding=binding,
        source_archive_raw=archive_raw,
        transcript_document=bundle_doc["partial_native_transcript"],
    )


def derive_v075_k7_owner_event_candidates_v1(
    *,
    role_manifest: Any,
    runtime_envelope: Any,
    business_bundle_raw: bytes,
) -> OwnerEventCandidateSetV1:
    """Join and independently replay production manifest/runtime/business bytes."""

    from acfqp import v075_k7_child_business_bundle_v1 as business_v1
    from acfqp import v075_k7_production_broker_runtime_v2 as runtime_v2
    from acfqp import v075_k7_production_role_manifest_v2 as manifest_v2
    from acfqp import v075_k7_successor_portable_replay_v1 as replay_v1

    if (
        type(role_manifest) is not manifest_v2.K7ProductionRoleManifestV2
        or type(runtime_envelope) is not runtime_v2.K7ProductionBrokerRuntimeEnvelopeV2
        or type(business_bundle_raw) is not bytes
    ):
        _fail("production owner-event join received a foreign artifact")
    role_manifest.assert_current()
    request = role_manifest.request
    accounted = request.profile.accounted_profile
    transport = accounted.transport_profile
    lifecycle = accounted.private_replay_profile
    archive_raw = transport._archive_bytes  # noqa: SLF001
    closure = replay_v1.reconstruct_v075_k7_successor_portable_profile_closure_v1(
        source_archive_raw=archive_raw,
        transport_profile_raw=canonical_json_bytes(transport.to_document()),
        lifecycle_profile_raw=canonical_json_bytes(lifecycle.to_document()),
        successor_profile_raw=canonical_json_bytes(request.profile.to_document()),
    )
    replay = replay_v1.replay_v075_k7_successor_request_bytes_portable_v1(
        raw=request.canonical_bytes, profile_closure=closure
    )
    bundle = business_v1.verify_v075_k7_child_business_bundle_public_bytes_v1(
        raw=business_bundle_raw, expected_request_replay=replay
    )
    return _derive_v075_k7_owner_event_candidates_from_verified_bundle_v1(
        role_manifest=role_manifest,
        runtime_envelope=runtime_envelope,
        request_replay=replay,
        verified_business_bundle=bundle,
    )


def _verify_owner_event_candidate_set_document_v1(
    artifact: OwnerEventCandidateSetV1,
) -> dict[str, Any]:
    """Replay topology once and return its exact already-built document."""

    if type(artifact) is not OwnerEventCandidateSetV1:
        _fail("owner event verifier received a foreign artifact")
    document = artifact.to_document()
    if artifact.execution_binding.binding_id != document["execution_binding_id"]:
        _fail("owner event candidate execution binding changed")
    closure_by_id = {row.site_closure_id: row for row in artifact.site_closures}
    seen_events: list[str] = []
    for candidate in artifact.path_candidates:
        closures = [closure_by_id.get(value) for value in candidate.site_closure_ids]
        if (
            any(value is None for value in closures)
            or any(value.path != candidate.path for value in closures if value is not None)
        ):
            _fail("path candidate references a foreign site closure")
        flattened = tuple(
            event_id
            for closure in closures
            if closure is not None
            for event_id in closure.ordered_event_ids
        )
        if set(flattened) != set(candidate.ordered_event_ids):
            _fail("path candidate event set differs from its site closures")
        seen_events.extend(candidate.ordered_event_ids)
    if len(seen_events) != len(set(seen_events)):
        _fail("one runtime event resolves to multiple owner paths")
    _sha(document["owner_event_candidate_set_id"], "owner candidate set")
    return document


def verify_owner_event_candidate_set_v1(
    artifact: OwnerEventCandidateSetV1,
) -> None:
    """Replay the candidate topology and event conservation identities."""

    _verify_owner_event_candidate_set_document_v1(artifact)


__all__ = [
    "CANDIDATE_SET_DOMAIN",
    "ConstructionAccountingOwnerEventCandidatesV1Error",
    "EXPECTED_PATH_COUNT",
    "EXPECTED_SITE_COUNT",
    "OwnerBoundarySiteClosureV1",
    "OwnerEventCandidateSetV1",
    "OwnerEventExecutionBindingV1",
    "OwnerPathCounterCandidateV1",
    "POSITIVE_KIND",
    "PROPOSED_CONTRACT_VERSION",
    "SCHEMA_VERSION",
    "ZERO_KIND",
    "derive_v075_k7_owner_event_candidates_v1",
    "verify_owner_event_candidate_set_v1",
]
