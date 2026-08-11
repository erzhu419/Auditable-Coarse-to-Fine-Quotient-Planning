"""Bytes-only verifier for the query-bound eight-role accounting bundle.

This module does not import the worker, supervisor, occurrence producer, or
their private builders.  It replays canonical role bytes, the output-byte
fixed point, all five stage event chains, nine shared receipts, three
route-exclusive 202-record WorkVectors, and three exact 182-term projections.
Its positive claim is limited to this registered construction bundle; campaign
coverage, route selection, economics, and official execution remain locked.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
from pathlib import Path
import stat
from typing import Any, Mapping, NoReturn

from acfqp.accounting_v1 import ReducerEnum, RouteKindEnum, SHARED_AXES, WorkVectorV1, ComparisonVectorV1
from acfqp.actual_accounting_v1 import ActualProjectionProofV1, verify_actual_projection_v1
from acfqp import construction_accounting_live_v3 as live_v3
from acfqp import construction_accounting_registry_v6 as registry_v6
from acfqp import construction_output_bytes_fixed_point_v1 as fixed_v1
from acfqp import construction_shared_resource_receipts_v1 as shared_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_RENDERER_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_PATH_AGGREGATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_SHARED_MEASUREMENT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_SET_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_V1_DOMAIN,
    CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN,
    RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN,
    RUNTIME_TREE_MANIFEST_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROFILE_KEY = "construction_k7_query_bound_complete_bundle_independent_verifier_v1"
RUNTIME_PROFILE_KEY = "construction_k7_query_bound_accounted_runtime_v1"
SUPERVISOR_PROFILE_KEY = "construction_k7_query_bound_supervised_executor_v1"
ACCOUNTING_PROFILE_KEY = "construction_k7_query_bound_occurrence_accounting_v1"
VERIFICATION_PROFILE_DOMAIN = (
    CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_PROFILE_V1_DOMAIN
)
VERIFICATION_DOMAIN = CONSTRUCTION_K7_QUERY_BOUND_COMPLETE_BUNDLE_VERIFICATION_V1_DOMAIN
ROLE_ORDER = fixed_v1.REGISTERED_OPERATIONAL_ARTIFACT_ROLES
SHARED_PATHS = shared_v1.SHARED_RESOURCE_PATHS
MAX_ROLE_BYTES = 256 * 1024 * 1024
RUNTIME_IMPORT_READ_PASSES_UPPER = 2
_LOCAL_RECOVERY_PATH_PREFIXES = ("local.", "acquisition.", "build.")

TRACE_KEYS = {
    "artifact_role",
    "schema",
    "schema_version",
    "profile_key",
    "supervised_request_id",
    "runtime_preparation_id",
    "runtime_tree_id",
    "science_summary",
    "recorded_stages",
    "business_hash_invocations",
    "child_integrity_obligations",
    "child_protocol_obligations",
    "child_self_peak_working_bytes_diagnostic",
    "hash_measurement_window_start",
    "hash_measurement_window_end",
    "accounting_provenance_hashes_excluded",
    "global_hashlib_sha256_constructor_hook_present",
    "formal_counter_records_issued_by_worker",
    "occurrence_vector_issued_by_worker",
    "construction_only",
    "official_execution_allowed",
    "operational_trace_id",
}
SCIENCE_KEYS = {
    "occurrence_id",
    "accounted_continuation_id",
    "stage_accounting_result_id",
    "transaction_1_id",
    "replanning_1_id",
    "transaction_2_request_id",
    "transaction_2_id",
    "final_local_replanning_id",
    "direct_ground_fallback_id",
    "terminal_class",
    "terminal_code",
    "route_attempts",
    "route_successes",
    "route_failures",
    "solver_attempts",
    "solver_successes",
    "solver_failures",
    "stage_instance_count",
    "stage_local_counter_record_count",
    "local_transaction_count",
    "cumulative_local_ground_draw_count",
    "fallback_states_expanded",
    "fallback_actions_evaluated",
    "fallback_ground_steps",
    "fallback_outcome_rows",
    "fallback_bellman_backups",
}
BUSINESS_KEYS = {
    "artifact_role",
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_id",
    "accounted_continuation_id",
    "stage_accounting_result_id",
    "shared_measurement_id",
    "runtime_preparation",
    "supervised_request",
    "shared_measurement",
    "science_summary",
    "terminal_class",
    "terminal_code",
    "construction_only",
    "official_execution_allowed",
}
PREPARATION_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "source_closure",
    "runtime_manifest",
    "runtime_manifest_cap_profile",
    "runtime_entrypoint",
    "private_runtime_lease_required",
    "runtime_tree_build_charged_to_occurrence",
    "construction_only",
    "official_execution_allowed",
    "query_bound_runtime_preparation_id",
}
REQUEST_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "runtime_preparation_id",
    "runtime_tree_id",
    "input_inventory",
    "prepare_before_acquisition",
    "construction_only",
    "official_execution_allowed",
    "supervised_request_id",
}
MEASUREMENT_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "runtime_preparation_id",
    "runtime_tree_id",
    "source_closure_id",
    "supervised_request_id",
    "operational_trace_id",
    "occurrence_id",
    "accounted_continuation_id",
    "stage_accounting_result_id",
    "runtime_file_count",
    "runtime_total_bytes",
    "runtime_manifest_document_bytes",
    "input_file_count",
    "input_total_bytes",
    "request_bytes",
    "operational_trace_bytes",
    "child_wait4_peak_bytes",
    "parent_hash_invocations",
    "child_hash_invocations",
    "parent_integrity_obligations",
    "child_integrity_obligations",
    "parent_protocol_obligations",
    "child_protocol_obligations",
    "fixed_pre_output_values",
    "pre_output_mounted_bytes_peak",
    "mounted_peak_final_formula",
    "output_counter_record_pending_fixed_point_and_commit",
    "process_exit_successes",
    "process_exit_failures",
    "read_value_kind",
    "staged_value_kind",
    "working_value_kind",
    "construction_only",
    "formal_counter_records_issued_here",
    "official_execution_allowed",
    "shared_measurement_id",
}
RECEIPT_KEYS = {
    "schema",
    "schema_version",
    "proposed_contract_version",
    "profile_key",
    "occurrence_id",
    "supervised_execution_id",
    "shared_measurement_id",
    "path",
    "reducer",
    "value",
    "source_kind",
    "source_evidence_id",
    "stage_placeholder_record_ids",
    "output_fixed_point_profile_id",
    "complete_window_closed",
    "stage_placeholders_replaced_not_summed",
    "numeric_value_semantically_authorized_for_this_construction",
    "official_execution_allowed",
    "shared_resource_receipt_id",
}
RECEIPT_SET_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_id",
    "supervised_execution_id",
    "shared_measurement_id",
    "shared_resource_paths",
    "shared_resource_receipt_ids",
    "receipt_count",
    "all_nine_shared_paths_semantically_replayed",
    "official_execution_allowed",
    "shared_resource_receipt_set_id",
}
AGGREGATION_KEYS = {
    "schema",
    "schema_version",
    "profile_key",
    "occurrence_id",
    "supervised_execution_id",
    "path",
    "reducer",
    "value",
    "stage_record_ids",
    "source_kind",
    "source_evidence_id",
    "all_stage_instances_retained",
    "shared_stage_placeholders_replaced_not_summed",
    "path_aggregation_id",
}
PARENT_INTEGRITY_OBLIGATIONS = (
    "runtime-preparation-replayed",
    "five-input-canonical-digests-replayed",
    "runtime-cas-resolved",
    "private-runtime-lease-replayed",
    "child-completion-observed",
    "trace-canonical-and-content-id-replayed",
    "five-stage-event-chains-replayed",
    "science-summary-identity-chain-replayed",
    "resource-formulas-reconciled",
)
PARENT_PROTOCOL_OBLIGATIONS = (
    "request-identity-frozen-before-launch",
    "prepare-before-acquisition-enforced",
    "fresh-python-I-argv-executed",
    "single-process-launch-observed",
    "quiet-stdout-stderr-enforced",
    "worker-trace-schema-enforced",
    "stage-order-and-owner-chain-enforced",
    "terminal-route-reconciliation-enforced",
    "operational-cutoff-precedes-accounting-provenance",
)
CHILD_INTEGRITY_OBLIGATIONS = tuple(
    sorted(
        (
            "request-canonical-and-content-id-replayed",
            "input-source_trace-digest-replayed",
            "input-build_epoch_envelope-digest-replayed",
            "input-root_query_result-digest-replayed",
            "input-recovery_overlay-digest-replayed",
            "input-recovery_request-digest-replayed",
            "accounted-continuation-identity-replayed",
            "five-stage-inventory-replayed",
            "science-summary-derived-from-live-result",
            *(f"stage-{index:02d}-event-to-vector-replay" for index in range(1, 6)),
        )
    )
)
CHILD_PROTOCOL_OBLIGATIONS = tuple(
    sorted(
        (
            "request-profile-and-cutoff-bound",
            "all-scientific-inputs-frozen-before-acquisition",
            "two-local-transactions-precede-direct-fallback",
            "route-and-solver-reconciliation-derived",
            *(f"stage-{index:02d}-owner-and-sequence-binding" for index in range(1, 6)),
        )
    )
)
_VERIFICATION_ISSUER = object()


class ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error(ValueError):
    """The eight-role byte bundle failed exact independent replay."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error(
            f"{label} is not one content ID"
        ) from error


def _exact(document: Any, fields: set[str], label: str) -> dict[str, Any]:
    if type(document) is not dict or set(document) != fields:
        _fail(f"{label} field set changed")
    return document


def _replay_domain_document(
    document: dict[str, Any], *, id_field: str, domain: str, label: str
) -> str:
    payload = dict(document)
    observed = payload.pop(id_field, None)
    if observed != content_id(domain, payload):
        _fail(f"{label} content ID changed")
    return _cid(observed, label)


def _replay_legacy_source_domain_document(
    document: dict[str, Any], *, id_field: str, domain: str, label: str
) -> str:
    """Replay the frozen V0.75 source-runtime domains outside Phase3E registry."""

    payload = dict(document)
    observed = payload.pop(id_field, None)
    expected = hashlib.sha256(
        domain.encode("utf-8") + b"\x00" + canonical_json_bytes(payload)
    ).hexdigest()
    if observed != expected:
        _fail(f"{label} content ID changed")
    return _cid(observed, label)


def _verify_source_closure(document: Any) -> tuple[str, dict[str, tuple[str, int]]]:
    closure = _exact(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "closure_rule",
            "root_modules",
            "modules",
            "module_ids",
            "module_count",
            "all_sources_regular_files",
            "all_source_paths_symlink_free",
            "caller_supplied_source_bytes_replayed",
            "construction_only",
            "closure_id",
        },
        "runtime source closure",
    )
    modules = closure["modules"]
    roots = closure["root_modules"]
    if (
        closure["schema"] != "acfqp.v075_construction_source_closure.v2"
        or closure["schema_version"] != "2.0.0"
        or closure["profile_key"] != "v075_construction_source_runtime_v2"
        or closure["closure_rule"]
        != "RECURSIVE_STATIC_MULTIROOT_LOCAL_ACFQP_IMPORTS"
        or type(modules) is not list
        or not modules
        or type(roots) is not list
        or roots != sorted(set(roots))
        or "acfqp.construction_k7_query_bound_accounted_runtime_v1" not in roots
        or any(
            root != "acfqp.construction_k7_query_bound_accounted_runtime_v1"
            and not root.startswith("acfqp.v075_")
            for root in roots
        )
        or not any(root.startswith("acfqp.v075_") for root in roots)
        or closure["module_count"] != len(modules)
        or closure["all_sources_regular_files"] is not True
        or closure["all_source_paths_symlink_free"] is not True
        or closure["caller_supplied_source_bytes_replayed"] is not True
        or closure["construction_only"] is not True
    ):
        _fail("runtime source closure semantics changed")
    module_ids: list[str] = []
    by_path: dict[str, tuple[str, int]] = {}
    names: list[str] = []
    imports_by_name: dict[str, list[str]] = {}
    for candidate in modules:
        module = _exact(
            candidate,
            {
                "schema",
                "schema_version",
                "profile_key",
                "module_name",
                "relative_path",
                "is_package",
                "source_sha256",
                "source_byte_count",
                "static_local_imports",
                "regular_file_verified",
                "symlink_free_verified",
                "module_id",
            },
            "runtime source module",
        )
        module_id = _replay_legacy_source_domain_document(
            module,
            id_field="module_id",
            domain="acfqp:v075-construction-source-module:v2",
            label="runtime source module",
        )
        path = module["relative_path"]
        name = module["module_name"]
        if (
            module["schema"] != "acfqp.v075_construction_source_module.v2"
            or module["schema_version"] != "2.0.0"
            or module["profile_key"] != "v075_construction_source_runtime_v2"
            or type(path) is not str
            or not path
            or path.startswith("/")
            or ".." in Path(path).parts
            or type(name) is not str
            or not name
            or type(module["is_package"]) is not bool
            or type(module["source_byte_count"]) is not int
            or module["source_byte_count"] <= 0
            or type(module["static_local_imports"]) is not list
            or module["static_local_imports"] != sorted(set(module["static_local_imports"]))
            or module["regular_file_verified"] is not True
            or module["symlink_free_verified"] is not True
            or path in by_path
            or name in imports_by_name
        ):
            _fail("runtime source module semantics changed")
        _cid(module["source_sha256"], "runtime source digest")
        by_path[path] = (module["source_sha256"], module["source_byte_count"])
        names.append(name)
        imports_by_name[name] = module["static_local_imports"]
        module_ids.append(module_id)
    name_set = set(names)
    if (
        names != sorted(set(names))
        or not set(roots) <= name_set
        or any(not set(imports) <= name_set for imports in imports_by_name.values())
        or closure["module_ids"] != module_ids
    ):
        _fail("runtime source closure graph changed")
    closure_id = _replay_legacy_source_domain_document(
        closure,
        id_field="closure_id",
        domain="acfqp:v075-construction-source-closure:v2",
        label="runtime source closure",
    )
    return closure_id, by_path


def _verify_runtime_manifest(
    document: Any, source_by_path: Mapping[str, tuple[str, int]]
) -> tuple[str, int, int]:
    manifest = _exact(
        document,
        {"schema", "schema_version", "tree_semantics_id", "entries", "runtime_tree_id"},
        "runtime manifest",
    )
    entries = manifest["entries"]
    if (
        manifest["schema"] != "acfqp.runtime_tree_manifest.v1"
        or manifest["tree_semantics_id"] != "acfqp-python-runtime-tree-v1"
        or type(entries) is not list
        or not entries
    ):
        _fail("runtime manifest semantics changed")
    paths: list[str] = []
    total_bytes = 0
    for entry in entries:
        if (
            type(entry) is not dict
            or set(entry) != {"relative_path", "size_bytes", "sha256"}
            or type(entry["relative_path"]) is not str
            or type(entry["size_bytes"]) is not int
            or entry["size_bytes"] < 0
        ):
            _fail("runtime manifest entry changed")
        _cid(entry["sha256"], "runtime manifest entry digest")
        path = entry["relative_path"]
        if source_by_path.get(path) != (entry["sha256"], entry["size_bytes"]):
            _fail("runtime manifest crossed its source closure")
        paths.append(path)
        total_bytes += entry["size_bytes"]
    if paths != sorted(set(paths)) or set(paths) != set(source_by_path):
        _fail("runtime manifest path inventory changed")
    runtime_tree_id = _replay_domain_document(
        manifest,
        id_field="runtime_tree_id",
        domain=RUNTIME_TREE_MANIFEST_DOMAIN,
        label="runtime manifest",
    )
    return runtime_tree_id, len(entries), total_bytes


def _verify_runtime_cap_profile(document: Any) -> dict[str, Any]:
    profile = _exact(
        document,
        {
            "schema",
            "schema_version",
            "profile_key",
            "max_file_count",
            "max_total_bytes",
            "max_manifest_document_bytes",
            "max_path_bytes",
            "factory_working_bytes_cap",
            "tree_passes",
            "runtime_manifest_cap_profile_id",
        },
        "runtime manifest cap profile",
    )
    if (
        profile["schema"] != "acfqp.runtime_manifest_cap_profile.v1"
        or profile["schema_version"] != SCHEMA_VERSION
        or profile["profile_key"] != "phase3e-runtime-manifest-caps-v2"
        or profile["max_file_count"] != 512
        or profile["max_total_bytes"] != 16 * 1024 * 1024
        or profile["max_manifest_document_bytes"] != 1024 * 1024
        or profile["max_path_bytes"] != 512
        or profile["factory_working_bytes_cap"] != 64 * 1024 * 1024
        or profile["tree_passes"] != 4
    ):
        _fail("runtime manifest cap profile changed")
    _replay_domain_document(
        profile,
        id_field="runtime_manifest_cap_profile_id",
        domain=RUNTIME_MANIFEST_CAP_PROFILE_DOMAIN,
        label="runtime manifest cap profile",
    )
    return profile


def _read_roles(directory: Path) -> tuple[dict[str, bytes], dict[str, dict[str, Any]]]:
    if directory.is_symlink():
        _fail("bundle directory must not be one symbolic link")
    root = directory.resolve(strict=True)
    info = root.stat()
    if root.is_symlink() or not root.is_dir() or stat.S_IMODE(info.st_mode) & 0o077:
        _fail("bundle directory is not one private real directory")
    expected_names = tuple(sorted(f"{role}.json" for role in ROLE_ORDER))
    if tuple(sorted(path.name for path in root.iterdir())) != expected_names:
        _fail("bundle directory role inventory changed")
    raw_by_role: dict[str, bytes] = {}
    doc_by_role: dict[str, dict[str, Any]] = {}
    for role in ROLE_ORDER:
        path = root / f"{role}.json"
        item = path.stat()
        if (
            path.is_symlink()
            or not path.is_file()
            or item.st_size <= 0
            or item.st_size > MAX_ROLE_BYTES
            or stat.S_IMODE(item.st_mode) & 0o177
        ):
            _fail(f"bundle role {role} is not one private regular file")
        raw = path.read_bytes()
        document = loads_canonical_json(raw)
        if type(document) is not dict or canonical_json_bytes(document) != raw:
            _fail(f"bundle role {role} is not canonical JSON")
        if document.get("artifact_role") != role:
            _fail(f"bundle role {role} label changed")
        raw_by_role[role] = raw
        doc_by_role[role] = document
    return raw_by_role, doc_by_role


@dataclass(frozen=True, slots=True)
class QueryBoundCompleteBundleVerificationV1:
    _issuer: InitVar[object]
    verification_profile_id: str
    occurrence_id: str
    operational_trace_id: str
    shared_measurement_id: str
    shared_receipt_set_id: str
    work_vector_ids: tuple[str, ...]
    comparison_vector_ids: tuple[str, ...]
    projection_proof_ids: tuple[str, ...]
    output_bytes: int
    role_digests: tuple[tuple[str, str], ...]
    _verification_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _VERIFICATION_ISSUER:
            _fail("complete-bundle verification result is caller-minted")
        for value, label in (
            (self.verification_profile_id, "verification profile"),
            (self.occurrence_id, "occurrence"),
            (self.operational_trace_id, "operational trace"),
            (self.shared_measurement_id, "shared measurement"),
            (self.shared_receipt_set_id, "shared receipt set"),
            *((value, "work vector") for value in self.work_vector_ids),
            *((value, "comparison vector") for value in self.comparison_vector_ids),
            *((value, "projection proof") for value in self.projection_proof_ids),
            *((digest, "role digest") for _role, digest in self.role_digests),
        ):
            _cid(value, label)
        if (
            len(self.work_vector_ids) != 3
            or len(self.comparison_vector_ids) != 3
            or len(self.projection_proof_ids) != 3
            or tuple(role for role, _digest in self.role_digests) != ROLE_ORDER
            or type(self.output_bytes) is not int
            or self.output_bytes <= 0
        ):
            _fail("complete-bundle verification result changed")
        object.__setattr__(
            self,
            "_verification_id",
            content_id(VERIFICATION_DOMAIN, self._payload()),
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.construction_k7_query_bound_complete_bundle_verification.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "verification_profile_id": self.verification_profile_id,
            "occurrence_id": self.occurrence_id,
            "operational_trace_id": self.operational_trace_id,
            "shared_measurement_id": self.shared_measurement_id,
            "shared_resource_receipt_set_id": self.shared_receipt_set_id,
            "work_vector_ids": list(self.work_vector_ids),
            "comparison_vector_ids": list(self.comparison_vector_ids),
            "actual_projection_proof_ids": list(self.projection_proof_ids),
            "io.output_bytes": self.output_bytes,
            "role_digests": [
                {"artifact_role": role, "bytes_sha256": digest}
                for role, digest in self.role_digests
            ],
            "five_stage_event_chains_replayed": True,
            "nine_shared_resource_receipts_replayed": True,
            "three_route_exclusive_202_record_vectors_replayed": True,
            "three_182_term_projections_recomputed": True,
            "output_fixed_point_replayed": True,
            "bytes_only_independent_verifier": True,
            "producer_modules_imported": False,
            "upstream_scientific_identity_chain_joined": True,
            "scientific_planner_recomputed_by_this_verifier": False,
            "source_bytes_embedded_or_externally_anchored": False,
            "accounting_bundle_semantics_only": True,
            "campaign_closure_issued": False,
            "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
            "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
            "official_execution_allowed": False,
        }

    @property
    def verification_id(self) -> str:
        expected = content_id(VERIFICATION_DOMAIN, self._payload())
        if expected != self._verification_id:
            _fail("complete-bundle verification result changed after issuance")
        return expected

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "complete_bundle_verification_id": self.verification_id}

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())


def _verify_query_bound_complete_bundle_directory_v1(
    directory: str | Path,
) -> QueryBoundCompleteBundleVerificationV1:
    raw, docs = _read_roles(Path(directory))
    output_bytes = sum(len(value) for value in raw.values())
    manifest = _exact(
        docs["OUTPUT_MANIFEST"],
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "output_bytes_fixed_point_profile_id",
            "io.output_bytes",
            "ordered_preceding_roles",
            "output_manifest_self_extent_excluded_from_preceding_rows",
            "required_role_order",
        },
        "output manifest",
    )
    if (
        manifest["schema"] != "acfqp.construction_k7_query_bound_output_manifest.v1"
        or manifest["io.output_bytes"] != output_bytes
        or manifest["required_role_order"] != list(ROLE_ORDER)
        or manifest["output_manifest_self_extent_excluded_from_preceding_rows"] is not True
        or type(manifest["ordered_preceding_roles"]) is not list
        or len(manifest["ordered_preceding_roles"]) != len(ROLE_ORDER) - 1
    ):
        _fail("output manifest or fixed-point total changed")
    for role, row in zip(ROLE_ORDER[:-1], manifest["ordered_preceding_roles"], strict=True):
        if row != {
            "artifact_role": role,
            "byte_count": len(raw[role]),
            "bytes_sha256": hashlib.sha256(raw[role]).hexdigest(),
        }:
            _fail("output manifest preceding-role commitment changed")

    trace = _exact(docs["OPERATIONAL_TRACE"], TRACE_KEYS, "operational trace")
    trace_id = _replay_domain_document(
        trace,
        id_field="operational_trace_id",
        domain=CONSTRUCTION_K7_QUERY_BOUND_OPERATIONAL_TRACE_V1_DOMAIN,
        label="operational trace",
    )
    science = _exact(trace["science_summary"], SCIENCE_KEYS, "science summary")
    occurrence_id = _cid(science["occurrence_id"], "science occurrence")
    for key, value in science.items():
        if key.endswith("_id"):
            _cid(value, f"science {key}")
    if (
        trace["schema"] != "acfqp.construction_k7_query_bound_operational_trace.v1"
        or trace["schema_version"] != SCHEMA_VERSION
        or trace["profile_key"] != RUNTIME_PROFILE_KEY
        or trace["construction_only"] is not True
        or trace["official_execution_allowed"] is not False
        or science["terminal_class"] != "PLAN_CERTIFICATE"
        or science["terminal_code"] != "FULL_GROUND_FALLBACK"
        or (science["route_attempts"], science["route_successes"], science["route_failures"])
        != (1, 1, 0)
        or (science["solver_attempts"], science["solver_successes"], science["solver_failures"])
        != (1, 1, 0)
        or science["stage_instance_count"] != 5
        or science["stage_local_counter_record_count"] != 1_010
        or science["local_transaction_count"] != 2
        or science["cumulative_local_ground_draw_count"] != 25_344
        or (
            science["fallback_states_expanded"],
            science["fallback_actions_evaluated"],
            science["fallback_ground_steps"],
            science["fallback_outcome_rows"],
            science["fallback_bellman_backups"],
        )
        != (30, 96, 96, 1_440, 102)
        or trace["hash_measurement_window_start"]
        != "AFTER_RUNTIME_INFRASTRUCTURE_IMPORTS"
        or trace["hash_measurement_window_end"]
        != "AFTER_STAGE_AND_TERMINAL_REPLAY_BEFORE_TRACE_PROVENANCE"
        or trace["accounting_provenance_hashes_excluded"] is not True
        or trace["global_hashlib_sha256_constructor_hook_present"] is not True
        or trace["formal_counter_records_issued_by_worker"] is not False
        or trace["occurrence_vector_issued_by_worker"] is not False
    ):
        _fail("operational trace scientific semantics changed")

    registry = registry_v6.official_counter_registry_v6()
    stage_profile = registry_v6.official_stage_profile_v6(registry)
    comparison_profile = registry_v6.official_comparison_profile_v6(registry)
    actual_profile = registry_v6.official_actual_projection_profile_v6(
        registry, comparison_profile
    )
    if type(trace["recorded_stages"]) is not list or len(trace["recorded_stages"]) != 5:
        _fail("operational trace stage inventory changed")
    stages = tuple(
        live_v3.RecordedStageWorkV3.from_document(
            row, registry, stage_profile, comparison_profile, actual_profile
        )
        for row in trace["recorded_stages"]
    )
    if tuple(row.stage_start.stage_kind.value for row in stages) != (
        "OPEN_INCREMENTAL_ACQUISITION",
        "OPEN_CHECKPOINT_REPLANNING",
        "OPEN_INCREMENTAL_ACQUISITION",
        "OPEN_CHECKPOINT_REPLANNING",
        "DIRECT_FALLBACK",
    ):
        _fail("operational trace stage order changed")

    business = _exact(docs["BUSINESS_RESULT"], BUSINESS_KEYS, "business result")
    preparation = _exact(
        business["runtime_preparation"], PREPARATION_KEYS, "runtime preparation"
    )
    preparation_id = _replay_domain_document(
        preparation,
        id_field="query_bound_runtime_preparation_id",
        domain=CONSTRUCTION_K7_QUERY_BOUND_RUNTIME_PREPARATION_V1_DOMAIN,
        label="runtime preparation",
    )
    request = _exact(business["supervised_request"], REQUEST_KEYS, "supervised request")
    request_id = _replay_domain_document(
        request,
        id_field="supervised_request_id",
        domain=CONSTRUCTION_K7_QUERY_BOUND_SUPERVISED_REQUEST_V1_DOMAIN,
        label="supervised request",
    )
    source_closure = preparation.get("source_closure")
    runtime_manifest = preparation.get("runtime_manifest")
    input_inventory = request.get("input_inventory")
    if (
        preparation.get("schema")
        != "acfqp.construction_k7_query_bound_runtime_preparation.v1"
        or preparation.get("schema_version") != SCHEMA_VERSION
        or preparation.get("proposed_contract_version") != "2.0.97"
        or preparation.get("profile_key") != SUPERVISOR_PROFILE_KEY
        or preparation.get("runtime_entrypoint")
        != "acfqp/construction_k7_query_bound_accounted_runtime_v1.py"
        or preparation.get("private_runtime_lease_required") is not True
        or preparation.get("runtime_tree_build_charged_to_occurrence") is not False
        or preparation.get("construction_only") is not True
        or preparation.get("official_execution_allowed") is not False
        or type(source_closure) is not dict
        or type(runtime_manifest) is not dict
        or type(input_inventory) is not list
        or len(input_inventory) != 5
        or request.get("schema")
        != "acfqp.construction_k7_query_bound_supervised_request.v1"
        or request.get("schema_version") != SCHEMA_VERSION
        or request.get("profile_key") != SUPERVISOR_PROFILE_KEY
        or request.get("runtime_preparation_id") != preparation_id
        or request.get("prepare_before_acquisition") is not True
        or request.get("construction_only") is not True
        or request.get("official_execution_allowed") is not False
    ):
        _fail("runtime preparation or supervised request semantics changed")
    source_closure_id, source_by_path = _verify_source_closure(source_closure)
    runtime_tree_id, runtime_file_count, runtime_total_bytes = _verify_runtime_manifest(
        runtime_manifest, source_by_path
    )
    runtime_cap_profile = _verify_runtime_cap_profile(
        preparation["runtime_manifest_cap_profile"]
    )
    if (
        runtime_file_count > runtime_cap_profile["max_file_count"]
        or runtime_total_bytes > runtime_cap_profile["max_total_bytes"]
        or len(canonical_json_bytes(runtime_manifest))
        > runtime_cap_profile["max_manifest_document_bytes"]
        or any(
            len(path.encode("utf-8")) > runtime_cap_profile["max_path_bytes"]
            for path in source_by_path
        )
    ):
        _fail("runtime source closure exceeds its frozen cap profile")
    if request.get("runtime_tree_id") != runtime_tree_id:
        _fail("supervised request crossed runtime trees")
    input_total_bytes = 0
    expected_input_roles = (
        ("SOURCE_TRACE", "source_trace.json"),
        ("BUILD_EPOCH_ENVELOPE", "build_epoch_envelope.json"),
        ("ROOT_QUERY_RESULT", "root_query_result.json"),
        ("RECOVERY_OVERLAY", "recovery_overlay.json"),
        ("RECOVERY_REQUEST", "recovery_request.json"),
    )
    for row, (role, filename) in zip(input_inventory, expected_input_roles, strict=True):
        if (
            type(row) is not dict
            or set(row) != {"role", "filename", "byte_count", "sha256"}
            or row["role"] != role
            or row["filename"] != filename
            or type(row["byte_count"]) is not int
            or row["byte_count"] <= 0
        ):
            _fail("supervised request input inventory changed")
        _cid(row["sha256"], "supervised input digest")
        input_total_bytes += row["byte_count"]

    measurement = _exact(
        business["shared_measurement"], MEASUREMENT_KEYS, "shared measurement"
    )
    measurement_id = _replay_domain_document(
        measurement,
        id_field="shared_measurement_id",
        domain=CONSTRUCTION_K7_QUERY_BOUND_SHARED_MEASUREMENT_V1_DOMAIN,
        label="shared measurement",
    )
    if (
        business["schema"] != "acfqp.construction_k7_query_bound_business_result.v1"
        or business["schema_version"] != SCHEMA_VERSION
        or business["profile_key"] != ACCOUNTING_PROFILE_KEY
        or business["occurrence_id"] != occurrence_id
        or business["science_summary"] != science
        or business["accounted_continuation_id"] != science["accounted_continuation_id"]
        or business["stage_accounting_result_id"] != science["stage_accounting_result_id"]
        or business["shared_measurement_id"] != measurement_id
        or business["terminal_class"] != "PLAN_CERTIFICATE"
        or business["terminal_code"] != "FULL_GROUND_FALLBACK"
        or business["construction_only"] is not True
        or business["official_execution_allowed"] is not False
        or measurement["schema"]
        != "acfqp.construction_k7_query_bound_shared_measurement.v1"
        or measurement["schema_version"] != SCHEMA_VERSION
        or measurement["proposed_contract_version"] != "2.0.97"
        or measurement["profile_key"] != SUPERVISOR_PROFILE_KEY
        or measurement["runtime_preparation_id"] != preparation_id
        or measurement["runtime_tree_id"] != runtime_tree_id
        or measurement["source_closure_id"] != source_closure_id
        or measurement["supervised_request_id"] != request_id
        or measurement["occurrence_id"] != occurrence_id
        or measurement["operational_trace_id"] != trace_id
        or measurement["accounted_continuation_id"]
        != science["accounted_continuation_id"]
        or measurement["stage_accounting_result_id"] != science["stage_accounting_result_id"]
        or measurement["input_file_count"] != 5
        or measurement["input_total_bytes"] != input_total_bytes
        or measurement["request_bytes"] != len(canonical_json_bytes(request))
        or measurement["operational_trace_bytes"] != len(raw["OPERATIONAL_TRACE"])
        or measurement["runtime_manifest_document_bytes"]
        != len(canonical_json_bytes(runtime_manifest))
        or measurement["runtime_file_count"] != runtime_file_count
        or measurement["runtime_total_bytes"] != runtime_total_bytes
        or measurement["parent_integrity_obligations"]
        != list(PARENT_INTEGRITY_OBLIGATIONS)
        or measurement["child_integrity_obligations"]
        != list(CHILD_INTEGRITY_OBLIGATIONS)
        or measurement["parent_protocol_obligations"]
        != list(PARENT_PROTOCOL_OBLIGATIONS)
        or measurement["child_protocol_obligations"]
        != list(CHILD_PROTOCOL_OBLIGATIONS)
        or measurement["process_exit_successes"] != 1
        or measurement["process_exit_failures"] != 0
        or measurement["mounted_peak_final_formula"]
        != "max(pre_output_peak,io.output_bytes)"
        or measurement["output_counter_record_pending_fixed_point_and_commit"] is not True
        or measurement["construction_only"] is not True
        or measurement["formal_counter_records_issued_here"] is not False
        or measurement["official_execution_allowed"] is not False
    ):
        _fail("business result, measurement, and trace identities crossed")
    if any(
        type(measurement[field]) is not int or measurement[field] <= 0
        for field in (
            "runtime_file_count",
            "runtime_total_bytes",
            "runtime_manifest_document_bytes",
            "input_file_count",
            "input_total_bytes",
            "request_bytes",
            "operational_trace_bytes",
            "child_wait4_peak_bytes",
            "parent_hash_invocations",
            "child_hash_invocations",
        )
    ) or (
        type(trace["child_self_peak_working_bytes_diagnostic"]) is not int
        or trace["child_self_peak_working_bytes_diagnostic"] <= 0
    ):
        _fail("shared measurement contains a nonpositive or noninteger observation")
    if (
        trace["supervised_request_id"] != request_id
        or trace["runtime_preparation_id"] != preparation_id
        or trace["runtime_tree_id"] != runtime_tree_id
        or trace["child_integrity_obligations"] != list(CHILD_INTEGRITY_OBLIGATIONS)
        or trace["child_protocol_obligations"] != list(CHILD_PROTOCOL_OBLIGATIONS)
        or trace["business_hash_invocations"] != measurement["child_hash_invocations"]
    ):
        _fail("operational trace crossed its preparation or obligations")

    fixed_rows = measurement.get("fixed_pre_output_values")
    if type(fixed_rows) is not list:
        _fail("shared measurement fixed values are absent")
    fixed_values = {
        row["path"]: row["value"]
        for row in fixed_rows
        if type(row) is dict and set(row) == {"path", "value"}
    }
    expected_fixed = {
        "common.hash_invocations": measurement["parent_hash_invocations"]
        + measurement["child_hash_invocations"],
        "common.integrity_checks": len(measurement["parent_integrity_obligations"])
        + len(measurement["child_integrity_obligations"]),
        "common.protocol_checks": len(measurement["parent_protocol_obligations"])
        + len(measurement["child_protocol_obligations"]),
        "io.read_bytes": measurement["runtime_manifest_document_bytes"]
        + (
            runtime_cap_profile["tree_passes"]
            + RUNTIME_IMPORT_READ_PASSES_UPPER
        )
        * measurement["runtime_total_bytes"]
        + measurement["request_bytes"]
        + measurement["input_total_bytes"]
        + measurement["operational_trace_bytes"],
        "io.staged_bytes": measurement["runtime_total_bytes"]
        + measurement["request_bytes"]
        + measurement["input_total_bytes"],
        "memory.working_bytes_peak": measurement["child_wait4_peak_bytes"],
        "process.launches": 1,
    }
    pre_output_peak = (
        measurement["runtime_total_bytes"]
        + measurement["request_bytes"]
        + measurement["input_total_bytes"]
        + measurement["operational_trace_bytes"]
    )
    if (
        fixed_values != expected_fixed
        or fixed_rows
        != [
            {"path": path, "value": value}
            for path, value in sorted(expected_fixed.items())
        ]
        or measurement["pre_output_mounted_bytes_peak"] != pre_output_peak
        or measurement["read_value_kind"]
        != "VERIFIED_UPPER_BOUND_SEALED_RUNTIME_INPUTS_AND_TRACE"
        or measurement["staged_value_kind"]
        != "EXACT_PRIVATE_LEASE_REQUEST_AND_INPUT_BYTES"
        or measurement["working_value_kind"] != "TRUSTED_PARENT_WAIT4_PEAK"
    ):
        _fail("shared measurement arithmetic changed")

    renderer_id = content_id(
        CONSTRUCTION_K7_QUERY_BOUND_OUTPUT_RENDERER_V1_DOMAIN,
        {
            "supervised_execution_id": measurement_id,
            "occurrence_id": occurrence_id,
            "shared_measurement_id": measurement_id,
            "operational_trace_id": trace_id,
            "required_roles": list(ROLE_ORDER),
        },
    )
    fixed_profile = fixed_v1.freeze_output_bytes_fixed_point_profile_v1(
        renderer_id=renderer_id,
        execution_identity_id=measurement_id,
        max_total_bytes=512 * 1024 * 1024,
        role_byte_caps={role: 256 * 1024 * 1024 for role in ROLE_ORDER},
        max_iterations=32,
    )
    if (
        manifest["occurrence_id"] != occurrence_id
        or manifest["output_bytes_fixed_point_profile_id"] != fixed_profile.profile_id
    ):
        _fail("output fixed-point profile identity changed")

    record_set = _exact(
        docs["COUNTER_RECORD_SET"],
        {
            "artifact_role",
            "schema",
            "occurrence_id",
            "io.output_bytes",
            "shared_resource_receipt_set",
            "shared_resource_receipts",
            "component_counter_record_count",
            "counter_records_per_component",
            "path_aggregations",
            "component_counter_records",
        },
        "counter record set",
    )
    receipt_set = record_set.get("shared_resource_receipt_set")
    receipts = record_set.get("shared_resource_receipts")
    if type(receipt_set) is not dict or type(receipts) is not list or len(receipts) != 9:
        _fail("counter record set omitted nine receipts")
    receipt_ids: list[str] = []
    receipts_by_path: dict[str, dict[str, Any]] = {}
    for receipt in receipts:
        receipt = _exact(receipt, RECEIPT_KEYS, "shared receipt")
        receipt_id = _replay_domain_document(
            receipt,
            id_field="shared_resource_receipt_id",
            domain=CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_V1_DOMAIN,
            label="shared receipt",
        )
        path = receipt.get("path")
        if path in receipts_by_path:
            _fail("shared receipt path repeated")
        receipts_by_path[path] = receipt
        receipt_ids.append(receipt_id)
    if tuple(receipts_by_path) != SHARED_PATHS:
        _fail("shared receipt order or path set changed")
    receipt_set = _exact(receipt_set, RECEIPT_SET_KEYS, "shared receipt set")
    receipt_set_id = _replay_domain_document(
        receipt_set,
        id_field="shared_resource_receipt_set_id",
        domain=CONSTRUCTION_K7_QUERY_BOUND_SHARED_RECEIPT_SET_V1_DOMAIN,
        label="shared receipt set",
    )
    if (
        receipt_set.get("schema")
        != "acfqp.construction_k7_query_bound_shared_receipt_set.v1"
        or receipt_set.get("schema_version") != SCHEMA_VERSION
        or receipt_set.get("profile_key") != ACCOUNTING_PROFILE_KEY
        or receipt_set.get("shared_resource_receipt_ids") != receipt_ids
        or receipt_set.get("shared_resource_paths") != list(SHARED_PATHS)
        or receipt_set.get("shared_measurement_id") != measurement_id
        or receipt_set.get("supervised_execution_id") != measurement_id
        or receipt_set.get("occurrence_id") != occurrence_id
        or receipt_set.get("receipt_count") != 9
        or receipt_set.get("all_nine_shared_paths_semantically_replayed") is not True
        or receipt_set.get("official_execution_allowed") is not False
    ):
        _fail("shared receipt set identity chain changed")
    expected_shared = dict(expected_fixed)
    expected_shared["io.output_bytes"] = output_bytes
    expected_shared["io.mounted_bytes_peak"] = max(pre_output_peak, output_bytes)
    for path in SHARED_PATHS:
        receipt = receipts_by_path[path]
        stage_ids = [
            next(item.record_id for item in stage.work_vector.records if item.path == path)
            for stage in stages
        ]
        if (
            receipt.get("value") != expected_shared[path]
            or receipt.get("schema")
            != "acfqp.construction_k7_query_bound_shared_receipt.v1"
            or receipt.get("schema_version") != SCHEMA_VERSION
            or receipt.get("proposed_contract_version") != "2.0.98"
            or receipt.get("profile_key") != ACCOUNTING_PROFILE_KEY
            or receipt.get("occurrence_id") != occurrence_id
            or receipt.get("supervised_execution_id") != measurement_id
            or receipt.get("shared_measurement_id") != measurement_id
            or receipt.get("reducer") != registry.by_path[path].reducer.value
            or receipt.get("stage_placeholder_record_ids") != stage_ids
            or receipt.get("complete_window_closed") is not True
            or receipt.get("stage_placeholders_replaced_not_summed") is not True
            or receipt.get("numeric_value_semantically_authorized_for_this_construction") is not True
            or receipt.get("official_execution_allowed") is not False
            or receipt.get("source_kind")
            != ("OUTPUT_FIXED_POINT" if path == "io.output_bytes" else "TRUSTED_SUPERVISOR_MEASUREMENT")
            or receipt.get("source_evidence_id")
            != (fixed_profile.profile_id if path == "io.output_bytes" else measurement_id)
            or receipt.get("output_fixed_point_profile_id")
            != (fixed_profile.profile_id if path == "io.output_bytes" else None)
        ):
            _fail(f"shared receipt semantics changed for {path}")

    work_doc = _exact(
        docs["WORK_VECTOR"],
        {
            "artifact_role",
            "schema",
            "io.output_bytes",
            "route_family_vectors_remain_separate",
            "marginal_route_upper_compliance_authority",
            "supervised_wrapper_work_vector",
            "local_recovery_work_vector",
            "direct_fallback_work_vector",
        },
        "work-vector artifact",
    )
    work_fields = (
        "supervised_wrapper_work_vector",
        "local_recovery_work_vector",
        "direct_fallback_work_vector",
    )
    vectors = tuple(WorkVectorV1.from_dict(work_doc[field], registry) for field in work_fields)
    if tuple(row.route_kind for row in vectors) != (
        RouteKindEnum.ABSTRACT_FAILED_PREFIX,
        RouteKindEnum.LOCAL_ATTEMPT,
        RouteKindEnum.DIRECT_FALLBACK,
    ):
        _fail("work-vector route-family sequence changed")
    comparison_doc = _exact(
        docs["COMPARISON_VECTOR"],
        {
            "artifact_role",
            "schema",
            "io.output_bytes",
            "route_choice_authority",
            "supervised_wrapper_comparison_vector",
            "local_recovery_comparison_vector",
            "direct_fallback_comparison_vector",
            "occurrence_reducer_exact_comparison_values",
        },
        "comparison-vector artifact",
    )
    comparison_fields = (
        "supervised_wrapper_comparison_vector",
        "local_recovery_comparison_vector",
        "direct_fallback_comparison_vector",
    )
    comparisons = tuple(
        ComparisonVectorV1.from_dict(comparison_doc[field])
        for field in comparison_fields
    )
    proof_doc = _exact(
        docs["ACTUAL_PROJECTION_PROOF"],
        {
            "artifact_role",
            "schema",
            "io.output_bytes",
            "supervised_wrapper_actual_projection_proof",
            "local_recovery_actual_projection_proof",
            "direct_fallback_actual_projection_proof",
        },
        "actual-projection-proof artifact",
    )
    proof_fields = (
        "supervised_wrapper_actual_projection_proof",
        "local_recovery_actual_projection_proof",
        "direct_fallback_actual_projection_proof",
    )
    proofs = tuple(ActualProjectionProofV1.from_dict(proof_doc[field]) for field in proof_fields)
    if (
        work_doc["schema"]
        != "acfqp.construction_k7_query_bound_work_vector_artifact.v1"
        or work_doc["io.output_bytes"] != output_bytes
        or work_doc["route_family_vectors_remain_separate"] is not True
        or work_doc["marginal_route_upper_compliance_authority"] is not False
        or comparison_doc["schema"]
        != "acfqp.construction_k7_query_bound_comparison_vector_artifact.v1"
        or comparison_doc["io.output_bytes"] != output_bytes
        or comparison_doc["route_choice_authority"] is not False
        or proof_doc["schema"]
        != "acfqp.construction_k7_query_bound_projection_artifact.v1"
        or proof_doc["io.output_bytes"] != output_bytes
    ):
        _fail("component artifact schema or authority boundary changed")
    for vector, comparison, proof in zip(vectors, comparisons, proofs, strict=True):
        verify_actual_projection_v1(
            proof,
            vector,
            comparison,
            registry,
            comparison_profile,
            actual_profile,
        )

    component_rows = record_set.get("component_counter_records")
    if (
        record_set["schema"]
        != "acfqp.construction_k7_query_bound_counter_record_set.v1"
        or record_set["occurrence_id"] != occurrence_id
        or record_set["io.output_bytes"] != output_bytes
        or record_set["component_counter_record_count"] != 606
        or record_set["counter_records_per_component"] != 202
        or type(component_rows) is not list
        or len(component_rows) != 3
    ):
        _fail("counter record component inventory changed")
    for row, vector in zip(component_rows, vectors, strict=True):
        if row != {
            "route_kind": vector.route_kind.value,
            "counter_records": [item.to_dict() for item in vector.records],
        }:
            _fail("counter-record role crossed its WorkVector")

    aggregations = record_set.get("path_aggregations")
    if type(aggregations) is not list or len(aggregations) != 202:
        _fail("occurrence path aggregation inventory changed")
    aggregation_values: dict[str, int] = {}
    stage_records_by_path = tuple(
        {item.path: item for item in stage.work_vector.records} for stage in stages
    )
    derived_values = {
        "process.exit_failures": 0,
        "process.exit_successes": 1,
        "route.attempts": science["route_attempts"],
        "route.failures": science["route_failures"],
        "route.successes": science["route_successes"],
        "solver.attempts": science["solver_attempts"],
        "solver.failures": science["solver_failures"],
        "solver.successes": science["solver_successes"],
    }
    for expected_path, candidate in zip(registry.required_paths, aggregations, strict=True):
        row = _exact(candidate, AGGREGATION_KEYS, "path aggregation")
        _replay_domain_document(
            row,
            id_field="path_aggregation_id",
            domain=CONSTRUCTION_K7_QUERY_BOUND_PATH_AGGREGATION_V1_DOMAIN,
            label="path aggregation",
        )
        path = row["path"]
        stage_rows = tuple(records[path] for records in stage_records_by_path)
        if path in receipts_by_path:
            expected_value = receipts_by_path[path]["value"]
            expected_kind = "SHARED_RESOURCE_RECEIPT"
            expected_evidence = receipts_by_path[path]["shared_resource_receipt_id"]
        elif path in derived_values:
            expected_value = derived_values[path]
            expected_kind = "SEMANTIC_DERIVED_RECONCILIATION"
            expected_evidence = trace_id
        elif registry.by_path[path].reducer is ReducerEnum.SUM:
            expected_value = sum(item.value for item in stage_rows)
            expected_kind = "STAGE_SUM"
            expected_evidence = measurement_id
        else:
            expected_value = max(item.value for item in stage_rows)
            expected_kind = "STAGE_MAX"
            expected_evidence = measurement_id
        if (
            path != expected_path
            or row["schema"] != "acfqp.construction_k7_query_bound_path_aggregation.v1"
            or row["schema_version"] != SCHEMA_VERSION
            or row["profile_key"] != ACCOUNTING_PROFILE_KEY
            or row["occurrence_id"] != occurrence_id
            or row["supervised_execution_id"] != measurement_id
            or row["reducer"] != registry.by_path[path].reducer.value
            or row["value"] != expected_value
            or row["stage_record_ids"] != [item.record_id for item in stage_rows]
            or row["source_kind"] != expected_kind
            or row["source_evidence_id"] != expected_evidence
            or row["all_stage_instances_retained"] is not True
            or row["shared_stage_placeholders_replaced_not_summed"]
            is not (path in SHARED_PATHS)
        ):
            _fail(f"path aggregation semantics changed for {path}")
        aggregation_values[path] = row["value"]
    for path in registry.required_paths:
        values = tuple(vector.values[path] for vector in vectors)
        reduced = sum(values) if registry.by_path[path].reducer is ReducerEnum.SUM else max(values)
        if reduced != aggregation_values[path]:
            _fail(f"component-to-occurrence reduction changed for {path}")
        if path.startswith(_LOCAL_RECOVERY_PATH_PREFIXES):
            expected_components = (0, aggregation_values[path], 0)
        elif path.startswith(("fallback.", "route.", "solver.")):
            expected_components = (0, 0, aggregation_values[path])
        elif path.startswith("control."):
            stage_values = tuple(records[path].value for records in stage_records_by_path)
            if registry.by_path[path].reducer is ReducerEnum.SUM:
                local_value = sum(stage_values[:4])
                fallback_value = stage_values[4]
            else:
                local_value = max(stage_values[:4])
                fallback_value = stage_values[4]
            expected_components = (0, local_value, fallback_value)
        else:
            expected_components = (aggregation_values[path], 0, 0)
        if values != expected_components:
            _fail(f"route-component provenance changed for {path}")

    aggregate_axes = tuple(
        (
            axis,
            (
                sum(comparison.value(axis) for comparison in comparisons)
                if next(item.reducer for item in comparison_profile.axes if item.name == axis)
                is ReducerEnum.SUM
                else max(comparison.value(axis) for comparison in comparisons)
            ),
        )
        for axis in SHARED_AXES
    )
    observed_axis_rows = comparison_doc.get("occurrence_reducer_exact_comparison_values")
    if observed_axis_rows != [
        {"axis": axis, "value": value} for axis, value in aggregate_axes
    ]:
        _fail("occurrence comparison aggregate changed")

    terminal = _exact(
        docs["TERMINAL_ARTIFACT"],
        {
            "artifact_role",
            "schema",
            "schema_version",
            "profile_key",
            "occurrence_id",
            "accounted_continuation_id",
            "direct_ground_fallback_id",
            "component_work_vector_ids",
            "component_comparison_vector_ids",
            "component_actual_projection_proof_ids",
            "io.output_bytes",
            "terminal_scope",
            "terminal_class",
            "terminal_code",
            "scientific_plan_certificate_preserved",
            "official_certificate_coverage_authority",
            "campaign_closure_issued",
            "official_execution_allowed",
        },
        "terminal artifact",
    )
    if (
        terminal["schema"] != "acfqp.construction_k7_query_bound_terminal_artifact.v1"
        or terminal["schema_version"] != SCHEMA_VERSION
        or terminal["profile_key"] != ACCOUNTING_PROFILE_KEY
        or terminal["occurrence_id"] != occurrence_id
        or terminal["accounted_continuation_id"] != science["accounted_continuation_id"]
        or terminal["direct_ground_fallback_id"] != science["direct_ground_fallback_id"]
        or terminal["component_work_vector_ids"] != [row.work_vector_id for row in vectors]
        or terminal["component_comparison_vector_ids"] != [row.comparison_vector_id for row in comparisons]
        or terminal["component_actual_projection_proof_ids"]
        != [row.actual_projection_proof_id for row in proofs]
        or terminal["io.output_bytes"] != output_bytes
        or terminal["terminal_scope"] != "LOGICAL_OCCURRENCE_CONSTRUCTION"
        or terminal["terminal_class"] != "PLAN_CERTIFICATE"
        or terminal["terminal_code"] != "FULL_GROUND_FALLBACK"
        or terminal["scientific_plan_certificate_preserved"] is not True
        or terminal["official_certificate_coverage_authority"] is not False
        or terminal["campaign_closure_issued"] is not False
        or terminal["official_execution_allowed"] is not False
    ):
        _fail("terminal artifact identity or authority boundary changed")

    profile_payload = {
        "schema": "acfqp.construction_k7_query_bound_complete_bundle_verification_profile.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "required_role_order": list(ROLE_ORDER),
        "required_stage_count": 5,
        "required_shared_receipt_count": 9,
        "required_component_vector_count": 3,
        "required_records_per_component": 202,
        "required_projection_terms_per_component": 182,
        "bytes_only": True,
        "producer_modules_forbidden": True,
        "scientific_planner_recomputation_required": False,
        "external_source_digest_anchor_required": False,
        "positive_claim_scope": "QUERY_BOUND_ACCOUNTING_BUNDLE_ONLY",
        "official_execution_allowed": False,
    }
    profile_id = content_id(VERIFICATION_PROFILE_DOMAIN, profile_payload)
    return QueryBoundCompleteBundleVerificationV1(
        _VERIFICATION_ISSUER,
        profile_id,
        occurrence_id,
        trace_id,
        measurement_id,
        receipt_set_id,
        tuple(row.work_vector_id for row in vectors),
        tuple(row.comparison_vector_id for row in comparisons),
        tuple(row.actual_projection_proof_id for row in proofs),
        output_bytes,
        tuple((role, hashlib.sha256(raw[role]).hexdigest()) for role in ROLE_ORDER),
    )


def verify_query_bound_complete_bundle_directory_v1(
    directory: str | Path,
) -> QueryBoundCompleteBundleVerificationV1:
    """Replay one exact private eight-role directory without producer imports."""

    try:
        return _verify_query_bound_complete_bundle_directory_v1(directory)
    except ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error:
        raise
    except Exception as error:
        raise ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error(
            "query-bound complete bundle replay failed"
        ) from error


__all__ = (
    "ConstructionK7QueryBoundCompleteBundleIndependentVerifierV1Error",
    "QueryBoundCompleteBundleVerificationV1",
    "verify_query_bound_complete_bundle_directory_v1",
)
