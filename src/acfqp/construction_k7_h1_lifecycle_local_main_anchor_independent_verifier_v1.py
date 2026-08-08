"""Independent verifier for caller-pinned H1 lifecycle Git provenance.

This module never imports the lifecycle-candidate producer.  It reads the
frozen program snapshot and all registered components from Git objects,
independently derives the 144 branch documents from the 62 transition rows,
and verifies the non-circular K -> C history.  The result is provenance only:
the expected anchor ID still comes from the caller and a worktree equality
check is an instantaneous observation, not an execution-byte authority.
"""

from __future__ import annotations

from dataclasses import InitVar, dataclass, field
import hashlib
import hmac
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_CALLER_PINNED_LIFECYCLE_PROVENANCE_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_MAIN_ANCHOR_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_SOURCE_REGISTRY_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN,
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
    parse_content_id,
)


SCHEMA_VERSION = "1.0.0"
PROPOSED_CONTRACT_VERSION = "2.0.59-A"
PROFILE_KEY = (
    "construction_k7_h1_lifecycle_local_main_anchor_independent_verifier_v1"
)
PREREGISTRATION_PROFILE_KEY = "construction_k7_h1_lifecycle_preregistration_v1"
TARGET_REF = "refs/heads/main"
ANCHOR_SCOPE = "CALLER_PINNED_LOCAL_GIT_PROVENANCE"
FINAL_PREREGISTRATION_REPOSITORY_PATH = (
    "specs/K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1.json"
)
PROGRAM_SNAPSHOT_REPOSITORY_PATH = (
    "specs/K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1.json"
)

SOURCE_REGISTRY_DOMAIN = (
    CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_SOURCE_REGISTRY_V1_DOMAIN
)
PROGRAM_SNAPSHOT_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN
FINAL_PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN
)
ANCHOR_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_MAIN_ANCHOR_V1_DOMAIN
PROVENANCE_DOMAIN = (
    CONSTRUCTION_K7_H1_CALLER_PINNED_LIFECYCLE_PROVENANCE_V1_DOMAIN
)
PROGRAM_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN
BRANCH_ANALYSIS_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN
)
if {
    SOURCE_REGISTRY_DOMAIN,
    PROGRAM_SNAPSHOT_DOMAIN,
    FINAL_PREREGISTRATION_DOMAIN,
    ANCHOR_DOMAIN,
    PROVENANCE_DOMAIN,
    PROGRAM_DOMAIN,
    BRANCH_ANALYSIS_DOMAIN,
} - PHASE3E_DOMAIN_TAGS:  # pragma: no cover - central registry invariant
    raise RuntimeError("H1 lifecycle provenance domains are not registered")


# Independently duplicated explicit boundary.  It is intentionally not called
# a dependency closure.
REQUIRED_COMPONENT_SPECS = (
    (
        "LIFECYCLE_PROGRAM_SNAPSHOT",
        PROGRAM_SNAPSHOT_REPOSITORY_PATH,
        "FROZEN_DECLARATIVE_PROGRAM_BYTES",
    ),
    (
        "LIFECYCLE_PROGRAM_CANDIDATE",
        "src/acfqp/construction_k7_h1_production_lifecycle_source_candidate_v1.py",
        "DECLARATIVE_PROGRAM_AND_ANALYSER",
    ),
    (
        "EXECUTION_TOPOLOGY",
        "src/acfqp/construction_k7_h1_execution_topology_profile_v1.py",
        "TOPOLOGY_SEMANTICS",
    ),
    (
        "OUTPUT_BRANCH_DAG_CANDIDATE",
        "src/acfqp/construction_k7_h1_production_output_upper_v1.py",
        "OUTPUT_TEMPLATE_SEMANTICS",
    ),
    (
        "SHARED_CAP_OWNER_V2",
        "src/acfqp/construction_k7_h1_shared_cap_owner_v2.py",
        "OWNER_MECHANICS",
    ),
    (
        "SHARED_RESOURCE_CATALOGUES",
        "src/acfqp/construction_k7_h1_shared_resource_catalogues_v1.py",
        "RESOURCE_TEMPLATE_CATALOGUES",
    ),
    (
        "BUSINESS_ADAPTER",
        "src/acfqp/construction_k7_h1_business_adapter_v1.py",
        "BUSINESS_ADAPTER_SEMANTICS",
    ),
    (
        "BROKER_IPC",
        "src/acfqp/construction_k7_h1_broker_ipc_v1.py",
        "BROKER_IPC_SEMANTICS",
    ),
    (
        "ACCOUNTING_V6_REPLAY",
        "src/acfqp/construction_accounting_semantic_verification_v6.py",
        "ACCOUNTING_SEMANTICS",
    ),
    (
        "CANONICAL_IDENTITY",
        "src/acfqp/phase3e_ids.py",
        "CONTENT_ID_SEMANTICS",
    ),
    (
        "PREREGISTRATION_PRODUCER",
        "src/acfqp/construction_k7_h1_lifecycle_preregistration_v1.py",
        "PREREGISTRATION_PRODUCER",
    ),
    (
        "INDEPENDENT_LOCAL_MAIN_VERIFIER",
        "src/acfqp/construction_k7_h1_lifecycle_local_main_anchor_independent_verifier_v1.py",
        "INDEPENDENT_GIT_OBJECT_VERIFIER",
    ),
)
EXACT_TEST_COMMAND = (
    "python3",
    "-m",
    "pytest",
    "-q",
    "-s",
    "tests/test_construction_k7_h1_lifecycle_local_main_anchor_v1.py",
)
DETERMINISTIC_ENVIRONMENT = (
    {"name": "LC_ALL", "value": "C.UTF-8"},
    {"name": "PYTHONDONTWRITEBYTECODE", "value": "1"},
    {"name": "PYTHONHASHSEED", "value": "0"},
    {"name": "TZ", "value": "UTC"},
)
SHARED_RESOURCE_PATHS = (
    "common.hash_invocations",
    "common.integrity_checks",
    "common.protocol_checks",
    "io.mounted_bytes_peak",
    "io.output_bytes",
    "io.read_bytes",
    "io.staged_bytes",
    "memory.working_bytes_peak",
    "process.launches",
)

_TYPED_NO_RESOURCE = {"kind": "NOT_APPLICABLE", "reason": "NO_SHARED_COST_LEAF"}
_TYPED_NO_AMBIGUITY = {
    "kind": "NOT_APPLICABLE",
    "reason": "NO_NATIVE_AMBIGUITY_EDGE",
}
_TYPED_FULL_SUCCESS = {"kind": "NOT_APPLICABLE", "reason": "FULL_SUCCESS"}

_COMPONENT_FIELDS = frozenset(
    {
        "role",
        "repository_path",
        "semantic_role",
        "git_mode",
        "git_blob_id",
        "sha256",
        "byte_count",
    }
)
_SOURCE_REGISTRY_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "profile_key",
        "components",
        "component_count",
        "registry_is_static_not_import_inferred",
        "git_object_database_only",
        "component_set_kind",
        "registered_component_set_complete",
        "transitive_dependency_closure_verified",
        "loaded_module_closure_verified",
        "exact_test_source_bound",
        "semantic_source_closure_present",
    }
)
_FINAL_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "anchor_scope",
        "target_ref",
        "expected_parent_commit_id",
        "source_registry",
        "source_registry_id",
        "lifecycle_program_snapshot_id",
        "lifecycle_program_id",
        "lifecycle_branch_analysis_id",
        "transition_count",
        "branch_count",
        "program_status",
        "exact_test_command",
        "deterministic_environment",
        "expected_parent_is_implementation_commit",
        "qualifying_commit_must_be_single_child_of_expected_parent",
        "first_qualifying_local_main_commit_required",
        "remote_published",
        "remote_anchor_claimed",
        "caller_pinned_local_git_provenance_only",
        "expected_anchor_id_source",
        "external_expected_anchor_binding_present",
        "zero_argument_self_mint_disabled",
        "fresh_import_self_mint_prevented",
        "source_authority_present",
        "execution_source_binding_present",
        "independent_snapshot_internal_replay_required",
        "snapshot_dependency_semantic_binding_complete",
        "component_registry_transitive_closure_complete",
        "live_dispatch_bound",
        "cleanup_continuation_bound",
        "production_execution_authorized",
        "formal_v7_route_authority_present",
        "counter_records_issued",
        "work_vector_issued",
        "comparison_vector_issued",
        "official_execution_allowed",
        "official_scalar_cost",
        "official_N_break_even",
        "counter_completeness_gate_status",
        "workload_economics_gate_status",
        "sample_efficiency_gate_status",
        "h1_lifecycle_final_preregistration_id",
    }
)
_SNAPSHOT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "snapshot_generation",
        "program",
        "branch_analysis_id",
        "branch_count",
        "program_status",
        "snapshot_is_runtime_source_authority",
        "production_execution_authorized",
        "official_execution_allowed",
        "h1_lifecycle_program_snapshot_id",
    }
)
_PROGRAM_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "proposed_contract_version",
        "profile_key",
        "h1_production_lifecycle_source_manifest_id",
        "h1_execution_topology_profile_id",
        "h1_production_output_branch_dag_id",
        "shared_resource_paths",
        "transition_count",
        "transitions",
        "single_table_drives_replay_and_failure_analysis",
        "shared_path_partition_scope",
        "candidate_table_partition_totality_present",
        "production_shared_path_partition_authority_present",
        "common_multiplicity_source_bound",
        "memory_binding_is_first",
        "output_reservation_precedes_first_launch",
        "all_mount_opens_precede_first_launch",
        "all_mount_closes_follow_descendant_reap",
        "mount_admission_universe",
        "created_output_roles_are_not_mounted_payload_admissions",
        "same_ofd_peak_read_follows_descendant_reap",
        "output_finalize_follows_mount_cleanup",
        "worker_then_business_launch_order",
        "worker_and_business_ambiguity_edges_present_in_candidate",
        "intended_owner_methods_are_strings_only",
        "shared_cap_owner_semantic_identity_bound",
        "owner_order_compatibility_claimed",
        "output_dag_role_presence_sets",
        "output_dag_role_presence_set_count",
        "linear_output_readback_roles",
        "linear_all_roles_matches_every_output_dag_leaf",
        "output_dag_leaf_join_bound",
        "output_read_lifecycle_complete",
        "numeric_ceiling_declared",
        "numeric_operand_issued",
        "live_runtime_integration_present",
        "production_execution_authority_present",
        "h1_production_lifecycle_program_id",
    }
)
_TRANSITION_FIELDS = frozenset(
    {
        "ordinal",
        "site_key",
        "phase",
        "operation",
        "resource_path",
        "owner_role",
        "intended_owner_method_string",
        "owner_method_semantic_identity_bound",
        "from_state",
        "success_state",
        "reservation_edge",
        "ambiguity_role",
        "failure_edges",
    }
)
_FAILURE_EDGE_FIELDS = frozenset(
    {
        "outcome",
        "current_site_admitted",
        "side_effect_may_have_started",
        "native_existence",
        "provisional_primary_cause_class",
        "provisional_primary_cause_code",
        "attempt_closure_issued",
        "terminal_classification_issued",
        "certificate_issued",
        "infeasibility_certified",
    }
)


class ConstructionK7H1LifecycleLocalMainAnchorV1Error(ValueError):
    """A caller-pinned lifecycle provenance invariant failed."""


class H1LifecycleLocalMainAnchorNotReadyV1(RuntimeError):
    """No complete two-commit local provenance record exists."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
            f"{label} must be one exact content ID"
        ) from error


def _oid(value: Any, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != 40
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(f"{label} must be one exact SHA-1 Git object ID")
    return value


def _safe_path(value: Any) -> str:
    if type(value) is not str or not value:
        _fail("component path is empty")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        _fail("component path is not canonical and relative")
    return value


def _git(root: Path, *arguments: str, binary: bool = False) -> str | bytes:
    environment = {
        "GIT_NO_REPLACE_OBJECTS": "1",
        "HOME": str(root),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PATH": "/usr/bin:/bin",
        "TZ": "UTC",
    }
    try:
        completed = subprocess.run(
            (
                "/usr/bin/git",
                "--no-replace-objects",
                "-C",
                str(root),
                *arguments,
            ),
            check=True,
            capture_output=True,
            env=environment,
        )
    except (OSError, subprocess.CalledProcessError) as error:
        raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
            f"Git object query failed: {' '.join(arguments)}"
        ) from error
    if binary:
        return bytes(completed.stdout)
    try:
        return completed.stdout.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
            "Git metadata was not ASCII"
        ) from error


def _verify_sha1_repository(root: Path) -> None:
    if _git(root, "rev-parse", "--show-object-format") != "sha1":
        _fail("repository object format must be exact SHA-1")
    if _git(root, "rev-parse", "--is-shallow-repository") != "false":
        _fail("shallow repositories cannot establish first-history provenance")


def _tree_blob(root: Path, commit_id: str, repository_path: str) -> tuple[str, str] | None:
    row = _git(root, "ls-tree", commit_id, "--", repository_path)
    if type(row) is not str or not row:
        return None
    fields = row.split(None, 3)
    if len(fields) != 4 or fields[1] != "blob" or fields[3] != repository_path:
        _fail("registered Git tree row is malformed")
    blob_id = _oid(fields[2], "Git blob")
    if _git(root, "cat-file", "-t", blob_id) != "blob":
        _fail("registered Git tree identity is not a blob")
    return fields[0], blob_id


def _read_blob(root: Path, commit_id: str, repository_path: str) -> bytes | None:
    row = _tree_blob(root, commit_id, repository_path)
    if row is None:
        return None
    raw = _git(root, "cat-file", "blob", row[1], binary=True)
    if type(raw) is not bytes or not raw:
        _fail("registered Git blob is empty")
    return raw


def _parents(root: Path, commit_id: str) -> tuple[str, ...]:
    if _git(root, "cat-file", "-t", commit_id) != "commit":
        _fail("history identity is not a commit")
    text = _git(root, "show", "-s", "--format=%P", commit_id)
    if type(text) is not str:
        _fail("Git parents are malformed")
    return tuple(_oid(value, "parent commit") for value in text.split() if value)


def _edge(
    outcome: str,
    admitted: bool,
    started: bool,
    native: str,
    cause_class: str,
    cause_code: str,
) -> dict[str, Any]:
    return {
        "outcome": outcome,
        "current_site_admitted": admitted,
        "side_effect_may_have_started": started,
        "native_existence": native,
        "provisional_primary_cause_class": cause_class,
        "provisional_primary_cause_code": cause_code,
        "attempt_closure_issued": False,
        "terminal_classification_issued": False,
        "certificate_issued": False,
        "infeasibility_certified": False,
    }


def _expected_failure_edges(operation: str) -> list[dict[str, Any]]:
    cap = _edge(
        "CAP_REJECTED_BEFORE_SIDE_EFFECT",
        False,
        False,
        "KNOWN_NOT_STARTED",
        "CAP_EXHAUSTION",
        "SHARED_CAP_EXHAUSTED",
    )
    callback_true = _edge(
        "CALLBACK_FAILED_AFTER_ADMISSION",
        True,
        True,
        "MAY_HAVE_STARTED",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    callback_false = _edge(
        "CALLBACK_FAILED_AFTER_ADMISSION",
        False,
        True,
        "MAY_HAVE_STARTED",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    ambiguous = _edge(
        "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION",
        True,
        True,
        "AMBIGUOUS",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    overrun_true = _edge(
        "OBSERVED_UPPER_BOUND_VIOLATION",
        True,
        True,
        "NOT_APPLICABLE",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    overrun_false = _edge(
        "OBSERVED_UPPER_BOUND_VIOLATION",
        False,
        True,
        "NOT_APPLICABLE",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    cleanup = _edge(
        "CLEANUP_FAILED",
        False,
        True,
        "MAY_HAVE_STARTED",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    protocol = _edge(
        "PROTOCOL_FAILED",
        False,
        False,
        "NOT_APPLICABLE",
        "PROTOCOL_FAILURE",
        "PROTOCOL_FAILURE",
    )
    if operation in {"MEMORY_BIND", "MOUNT_OPEN", "LAUNCH_CHILD"}:
        return [cap, ambiguous]
    if operation == "OUTPUT_RESERVE":
        return [cap]
    if operation in {"COMMON_HASH", "COMMON_INTEGRITY", "COMMON_PROTOCOL"}:
        return [cap, callback_true]
    if operation in {
        "STAGE_INPUT",
        "READ_INPUT",
        "READ_BUSINESS_RESULT",
        "OUTPUT_ROLE_READBACK",
    }:
        return [cap, callback_true, overrun_true]
    if operation == "SAME_OFD_PEAK_READ":
        return [callback_false, overrun_false]
    if operation == "MOUNT_CLOSE":
        return [cleanup]
    if operation in {"DESCENDANT_REAP", "OUTPUT_CLOSE"}:
        return [protocol]
    if operation == "OUTPUT_FINALIZE":
        return [callback_false, overrun_false, protocol]
    _fail("lifecycle transition has an unknown operation")


def _decoded_resource_path(row: Mapping[str, Any]) -> str | None:
    value = row["resource_path"]
    if type(value) is str and value in SHARED_RESOURCE_PATHS:
        return value
    if value == _TYPED_NO_RESOURCE:
        return None
    _fail("lifecycle transition has an invalid resource path")


def _verify_and_recompile_transitions(program: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows = program["transitions"]
    if type(rows) is not list or len(rows) != 62:
        _fail("lifecycle snapshot must contain exactly 62 transitions")
    rebuilt: list[dict[str, Any]] = []
    previous_state = "STATE_INITIAL"
    seen_sites: set[str] = set()
    for index, row in enumerate(rows, 1):
        if type(row) is not dict or frozenset(row) != _TRANSITION_FIELDS:
            _fail("lifecycle transition fields are not exact")
        for name in (
            "site_key",
            "phase",
            "operation",
            "owner_role",
            "intended_owner_method_string",
        ):
            if type(row[name]) is not str or not row[name]:
                _fail("lifecycle transition contains an empty static field")
        site_key = row["site_key"]
        if site_key in seen_sites:
            _fail("lifecycle transition site is duplicated")
        seen_sites.add(site_key)
        resource_path = _decoded_resource_path(row)
        if type(row["reservation_edge"]) is not bool or (
            row["reservation_edge"] and resource_path is None
        ):
            _fail("lifecycle reservation edge is malformed")
        expected_edges = _expected_failure_edges(row["operation"])
        if row["failure_edges"] != expected_edges or any(
            type(edge) is not dict or frozenset(edge) != _FAILURE_EDGE_FIELDS
            for edge in row["failure_edges"]
        ):
            _fail("lifecycle failure edges did not independently recompile")
        has_ambiguity = any(
            edge["outcome"] == "NATIVE_EXISTENCE_AMBIGUOUS_AFTER_ADMISSION"
            for edge in expected_edges
        )
        ambiguity = row["ambiguity_role"]
        if has_ambiguity:
            if ambiguity not in {"MEMORY_HIERARCHY", "MOUNT", "WORKER", "BUSINESS"}:
                _fail("lifecycle ambiguity role is malformed")
        elif ambiguity != _TYPED_NO_AMBIGUITY:
            _fail("non-ambiguous transition has a non-null ambiguity role")
        expected_state = f"STATE_AFTER_{site_key}"
        rebuilt_row = dict(row)
        rebuilt_row.update(
            {
                "ordinal": index,
                "owner_method_semantic_identity_bound": False,
                "from_state": previous_state,
                "success_state": expected_state,
                "resource_path": (
                    resource_path if resource_path is not None else dict(_TYPED_NO_RESOURCE)
                ),
                "ambiguity_role": (
                    ambiguity if has_ambiguity else dict(_TYPED_NO_AMBIGUITY)
                ),
                "failure_edges": expected_edges,
            }
        )
        if rebuilt_row != row:
            _fail("derived lifecycle transition fields changed")
        rebuilt.append(rebuilt_row)
        previous_state = expected_state
    if rebuilt[0]["operation"] != "MEMORY_BIND" or rebuilt[-1]["operation"] != "OUTPUT_CLOSE":
        _fail("lifecycle boundary operations changed")
    if {
        path
        for row in rebuilt
        if (path := _decoded_resource_path(row)) is not None
    } != set(SHARED_RESOURCE_PATHS):
        _fail("lifecycle transitions do not cover exactly nine shared paths")
    operation_positions: dict[str, list[int]] = {}
    for index, row in enumerate(rebuilt):
        operation_positions.setdefault(row["operation"], []).append(index)
    first_launch = min(operation_positions["LAUNCH_CHILD"])
    reap = operation_positions["DESCENDANT_REAP"][0]
    peak = operation_positions["SAME_OFD_PEAK_READ"][0]
    finalize = operation_positions["OUTPUT_FINALIZE"][0]
    if not (
        operation_positions["OUTPUT_RESERVE"][0] < first_launch
        and max(operation_positions["MOUNT_OPEN"]) < first_launch
        and reap < peak < min(operation_positions["MOUNT_CLOSE"])
        and max(operation_positions["MOUNT_CLOSE"]) < finalize
    ):
        _fail("lifecycle operation ordering invariants changed")
    launch_roles = [row["ambiguity_role"] for row in rebuilt if row["operation"] == "LAUNCH_CHILD"]
    if launch_roles != ["WORKER", "BUSINESS"]:
        _fail("worker/business launch order changed")
    return rebuilt


def _resource_prefix_documents(
    transitions: list[dict[str, Any]],
    completed_count: int,
    current: dict[str, Any] | None,
    edge: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    completed = transitions[:completed_count]
    completed_keys = {row["site_key"] for row in completed}
    attempted_keys = set(completed_keys)
    if current is not None:
        attempted_keys.add(current["site_key"])
    admitted_keys = {
        row["site_key"] for row in completed if row["reservation_edge"] is True
    }
    if current is not None and edge is not None and edge["current_site_admitted"] is True:
        admitted_keys.add(current["site_key"])
    result: list[dict[str, Any]] = []
    for path in SHARED_RESOURCE_PATHS:
        universe = [
            row["site_key"]
            for row in transitions
            if _decoded_resource_path(row) == path
        ]
        result.append(
            {
                "path": path,
                "attempted_site_prefix": [key for key in universe if key in attempted_keys],
                "admitted_site_prefix": [key for key in universe if key in admitted_keys],
                "completed_site_prefix": [key for key in universe if key in completed_keys],
                "unreached_site_keys": [key for key in universe if key not in attempted_keys],
                "partition_scope": "DECLARATIVE_CANDIDATE_TABLE_ONLY",
                "production_source_multiplicity_bound": False,
                "missing_as_zero_allowed": False,
                "wildcard_allowed": False,
            }
        )
    return result


def _derive_branch_documents(transitions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    branches: list[dict[str, Any]] = []
    for index, transition in enumerate(transitions):
        successful = [row["site_key"] for row in transitions[:index]]
        for edge in transition["failure_edges"]:
            branches.append(
                {
                    "branch_key": f"FAIL:{transition['site_key']}:{edge['outcome']}",
                    "branch_kind": "FIRST_FAILURE_PREFIX",
                    "first_failure_outcome": edge["outcome"],
                    "failed_site_key": transition["site_key"],
                    "failed_edge": edge,
                    "successful_site_prefix": successful,
                    "attempted_site_prefix": [*successful, transition["site_key"]],
                    "resource_prefixes": _resource_prefix_documents(
                        transitions, index, transition, edge
                    ),
                    "prefix_derived_from_transition_table": True,
                    "attempt_closure_issued": False,
                    "terminal_classification_issued": False,
                }
            )
    all_keys = [row["site_key"] for row in transitions]
    branches.append(
        {
            "branch_key": "SUCCESS:COMPLETE_LIFECYCLE",
            "branch_kind": "FULL_SUCCESS",
            "first_failure_outcome": dict(_TYPED_FULL_SUCCESS),
            "failed_site_key": dict(_TYPED_FULL_SUCCESS),
            "failed_edge": dict(_TYPED_FULL_SUCCESS),
            "successful_site_prefix": all_keys,
            "attempted_site_prefix": all_keys,
            "resource_prefixes": _resource_prefix_documents(
                transitions, len(transitions), None, None
            ),
            "prefix_derived_from_transition_table": True,
            "attempt_closure_issued": False,
            "terminal_classification_issued": False,
        }
    )
    if len({row["branch_key"] for row in branches}) != len(branches):
        _fail("derived lifecycle branch keys are not unique")
    return branches


def _verify_program_snapshot(raw: bytes) -> tuple[str, str, str, int, int]:
    try:
        snapshot = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
            "lifecycle program snapshot is not canonical JSON"
        ) from error
    if type(snapshot) is not dict or frozenset(snapshot) != _SNAPSHOT_FIELDS:
        _fail("lifecycle program snapshot fields are not exact")
    snapshot_id = _cid(snapshot["h1_lifecycle_program_snapshot_id"], "program snapshot")
    snapshot_payload = dict(snapshot)
    snapshot_payload.pop("h1_lifecycle_program_snapshot_id")
    if content_id(PROGRAM_SNAPSHOT_DOMAIN, snapshot_payload) != snapshot_id:
        _fail("lifecycle program snapshot ID did not replay")
    program = snapshot["program"]
    if type(program) is not dict or frozenset(program) != _PROGRAM_FIELDS:
        _fail("frozen lifecycle program fields are not exact")
    program_id = _cid(program["h1_production_lifecycle_program_id"], "lifecycle program")
    program_payload = dict(program)
    program_payload.pop("h1_production_lifecycle_program_id")
    if content_id(PROGRAM_DOMAIN, program_payload) != program_id:
        _fail("frozen lifecycle program ID did not replay")
    for name in (
        "h1_production_lifecycle_source_manifest_id",
        "h1_execution_topology_profile_id",
        "h1_production_output_branch_dag_id",
    ):
        _cid(program[name], name)
    transitions = _verify_and_recompile_transitions(program)
    branches = _derive_branch_documents(transitions)
    analysis_payload = {
        "schema": "acfqp.h1_production_lifecycle_branch_analysis.v1",
        "schema_version": "1.0.0",
        "h1_production_lifecycle_program_id": program_id,
        "branch_count": len(branches),
        "branch_count_formula": "ONE_PLUS_SUM_FAILURE_EDGES_OVER_TRANSITIONS",
        "branches": branches,
        "first_failure_prefixes_complete_for_declared_candidate_edges": True,
        "production_failure_edge_completeness_claimed": False,
        "shared_path_partitions_relative_to_candidate_table_only": True,
        "post_failure_cleanup_continuation_program_bound": False,
        "complete_attempt_branches_issued": False,
        "live_runtime_branch_completeness_claimed": False,
    }
    analysis_id = content_id(BRANCH_ANALYSIS_DOMAIN, analysis_payload)
    if (
        snapshot["schema"] != "acfqp.k7_h1_lifecycle_program_snapshot.v1"
        or snapshot["schema_version"] != SCHEMA_VERSION
        or snapshot["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or snapshot["profile_key"]
        != "construction_k7_h1_lifecycle_program_snapshot_v1"
        or snapshot["snapshot_generation"]
        != "ONE_TIME_MIGRATION_FROM_CONTRACT_2_0_58_D"
        or snapshot["program_status"] != "ANCHORED_MIGRATION_SEED_ONLY"
        or snapshot["snapshot_is_runtime_source_authority"] is not False
        or snapshot["production_execution_authorized"] is not False
        or snapshot["official_execution_allowed"] is not False
        or program["schema"] != "acfqp.h1_production_lifecycle_program.v1"
        or program["schema_version"] != "1.0.0"
        or program["proposed_contract_version"] != "2.0.58"
        or program["profile_key"]
        != "construction_k7_h1_production_lifecycle_source_candidate_v1"
        or program["shared_resource_paths"] != list(SHARED_RESOURCE_PATHS)
        or program["transition_count"] != len(transitions)
        or snapshot["branch_count"] != len(branches)
        or len(branches) != 144
        or snapshot["branch_analysis_id"] != analysis_id
    ):
        _fail("snapshot lifecycle semantics did not independently replay")
    expected_program_claims = {
        "single_table_drives_replay_and_failure_analysis": True,
        "shared_path_partition_scope": "DECLARATIVE_CANDIDATE_TABLE_ONLY",
        "candidate_table_partition_totality_present": True,
        "production_shared_path_partition_authority_present": False,
        "common_multiplicity_source_bound": False,
        "memory_binding_is_first": True,
        "output_reservation_precedes_first_launch": True,
        "all_mount_opens_precede_first_launch": True,
        "all_mount_closes_follow_descendant_reap": True,
        "mount_admission_universe": "SEALED_INPUT_TARGETS_ONLY",
        "created_output_roles_are_not_mounted_payload_admissions": True,
        "same_ofd_peak_read_follows_descendant_reap": True,
        "output_finalize_follows_mount_cleanup": True,
        "worker_then_business_launch_order": True,
        "worker_and_business_ambiguity_edges_present_in_candidate": True,
        "intended_owner_methods_are_strings_only": True,
        "shared_cap_owner_semantic_identity_bound": False,
        "owner_order_compatibility_claimed": False,
        "linear_all_roles_matches_every_output_dag_leaf": False,
        "output_dag_leaf_join_bound": False,
        "output_read_lifecycle_complete": False,
        "numeric_ceiling_declared": False,
        "numeric_operand_issued": False,
        "live_runtime_integration_present": False,
        "production_execution_authority_present": False,
    }
    if any(program.get(key) != value for key, value in expected_program_claims.items()):
        _fail("snapshot lifecycle claim boundary changed")
    role_sets = program["output_dag_role_presence_sets"]
    linear_roles = program["linear_output_readback_roles"]
    if (
        type(role_sets) is not list
        or not role_sets
        or program["output_dag_role_presence_set_count"] != len(role_sets)
        or any(type(row) is not list for row in role_sets)
        or type(linear_roles) is not list
        or not linear_roles
        or linear_roles not in role_sets
    ):
        _fail("snapshot output-role universe is malformed")
    return snapshot_id, program_id, analysis_id, len(transitions), len(branches)


def _parse_final(raw: bytes) -> dict[str, Any]:
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
            "final preregistration is not canonical JSON"
        ) from error
    if type(document) is not dict or frozenset(document) != _FINAL_FIELDS:
        _fail("final preregistration fields are not exact")
    final_id = _cid(document["h1_lifecycle_final_preregistration_id"], "final preregistration")
    payload = dict(document)
    payload.pop("h1_lifecycle_final_preregistration_id")
    if content_id(FINAL_PREREGISTRATION_DOMAIN, payload) != final_id:
        _fail("final preregistration content identity did not replay")
    registry = document["source_registry"]
    if type(registry) is not dict or frozenset(registry) != _SOURCE_REGISTRY_FIELDS:
        _fail("source registry fields are not exact")
    components = registry["components"]
    if (
        registry["schema"] != "acfqp.k7_h1_lifecycle_local_source_registry.v1"
        or registry["schema_version"] != SCHEMA_VERSION
        or registry["profile_key"] != PREREGISTRATION_PROFILE_KEY
        or registry["registry_is_static_not_import_inferred"] is not True
        or registry["git_object_database_only"] is not True
        or registry["component_set_kind"]
        != "EXPLICIT_NON_TRANSITIVE_PINNED_BOUNDARY"
        or registry["registered_component_set_complete"] is not True
        or any(
            registry[name] is not False
            for name in (
                "transitive_dependency_closure_verified",
                "loaded_module_closure_verified",
                "exact_test_source_bound",
                "semantic_source_closure_present",
            )
        )
        or type(components) is not list
        or registry["component_count"] != len(REQUIRED_COMPONENT_SPECS)
        or len(components) != len(REQUIRED_COMPONENT_SPECS)
    ):
        _fail("source registry changed its explicit non-transitive boundary")
    for row, expected in zip(components, REQUIRED_COMPONENT_SPECS):
        if (
            type(row) is not dict
            or frozenset(row) != _COMPONENT_FIELDS
            or (row["role"], row["repository_path"], row["semantic_role"]) != expected
            or row["git_mode"] != "100644"
            or type(row["byte_count"]) is not int
            or row["byte_count"] <= 0
        ):
            _fail("source-registry row differs from the pinned boundary")
        _safe_path(row["repository_path"])
        _oid(row["git_blob_id"], "component blob")
        _cid(row["sha256"], "component SHA-256")
    if content_id(SOURCE_REGISTRY_DOMAIN, dict(registry)) != _cid(
        document["source_registry_id"], "source registry"
    ):
        _fail("source registry content identity did not replay")
    for name in (
        "lifecycle_program_snapshot_id",
        "lifecycle_program_id",
        "lifecycle_branch_analysis_id",
    ):
        _cid(document[name], name)
    if (
        document["schema"] != "acfqp.k7_h1_lifecycle_final_preregistration.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"] != PREREGISTRATION_PROFILE_KEY
        or document["anchor_scope"] != ANCHOR_SCOPE
        or document["target_ref"] != TARGET_REF
        or document["transition_count"] != 62
        or document["branch_count"] != 144
        or document["program_status"] != "CALLER_PINNED_MIGRATION_SEED_ONLY"
        or document["exact_test_command"] != list(EXACT_TEST_COMMAND)
        or document["deterministic_environment"] != list(DETERMINISTIC_ENVIRONMENT)
        or document["expected_parent_is_implementation_commit"] is not True
        or document["qualifying_commit_must_be_single_child_of_expected_parent"] is not True
        or document["first_qualifying_local_main_commit_required"] is not True
        or document["caller_pinned_local_git_provenance_only"] is not True
        or document["expected_anchor_id_source"] != "CALLER_ARGUMENT"
        or document["zero_argument_self_mint_disabled"] is not True
        or document["independent_snapshot_internal_replay_required"] is not True
        or any(
            document[name] is not False
            for name in (
                "remote_published",
                "remote_anchor_claimed",
                "external_expected_anchor_binding_present",
                "fresh_import_self_mint_prevented",
                "source_authority_present",
                "execution_source_binding_present",
                "snapshot_dependency_semantic_binding_complete",
                "component_registry_transitive_closure_complete",
                "live_dispatch_bound",
                "cleanup_continuation_bound",
                "production_execution_authorized",
                "formal_v7_route_authority_present",
                "counter_records_issued",
                "work_vector_issued",
                "comparison_vector_issued",
                "official_execution_allowed",
            )
        )
        or document["official_scalar_cost"] is not None
        or document["official_N_break_even"] is not None
        or document["counter_completeness_gate_status"]
        != "COUNTER_COMPLETENESS_GATE_NOT_RUN"
        or document["workload_economics_gate_status"]
        != "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
        or document["sample_efficiency_gate_status"]
        != "SAMPLE_EFFICIENCY_GATE_NOT_RUN"
    ):
        _fail("final preregistration changed its locked provenance semantics")
    _oid(document["expected_parent_commit_id"], "expected parent commit")
    return document


def _verify_components_at_commit(
    root: Path, commit_id: str, document: Mapping[str, Any]
) -> None:
    for row in document["source_registry"]["components"]:
        tree = _tree_blob(root, commit_id, row["repository_path"])
        if tree != (row["git_mode"], row["git_blob_id"]):
            _fail("registered component Git mode/blob changed")
        raw = _read_blob(root, commit_id, row["repository_path"])
        if (
            raw is None
            or len(raw) != row["byte_count"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]
        ):
            _fail("registered component bytes changed")


def _verify_exact_qualifying_diff(
    root: Path, parent_id: str, commit_id: str, final_blob_id: str
) -> None:
    raw = _git(
        root,
        "diff-tree",
        "--no-commit-id",
        "--raw",
        "--no-abbrev",
        "--no-renames",
        "-r",
        parent_id,
        commit_id,
    )
    if type(raw) is not str:
        _fail("qualifying commit diff is malformed")
    match = re.fullmatch(
        rf":000000 100644 {'0' * 40} ({'[0-9a-f]' + '{40}'}) A\t"
        + re.escape(FINAL_PREREGISTRATION_REPOSITORY_PATH),
        raw,
    )
    if match is None or match.group(1) != final_blob_id:
        _fail("qualifying commit does not add exactly one 100644 preregistration")


_ANCHOR_ISSUER = object()
_PROVENANCE_ISSUER = object()


@dataclass(frozen=True, slots=True)
class H1LifecycleLocalMainAnchorAttestationV1:
    _issuer: InitVar[object]
    commit_id: str
    tree_id: str
    parent_commit_id: str
    final_preregistration_blob_id: str
    final_preregistration_id: str
    source_registry_id: str
    program_snapshot_id: str
    program_id: str
    branch_analysis_id: str
    _anchor_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _ANCHOR_ISSUER:
            _fail("local-main lifecycle anchor is verifier-issued only")
        for value in (
            self.commit_id,
            self.tree_id,
            self.parent_commit_id,
            self.final_preregistration_blob_id,
        ):
            _oid(value, "anchor Git identity")
        for value in (
            self.final_preregistration_id,
            self.source_registry_id,
            self.program_snapshot_id,
            self.program_id,
            self.branch_analysis_id,
        ):
            _cid(value, "anchor content identity")
        object.__setattr__(self, "_anchor_id", content_id(ANCHOR_DOMAIN, self._payload()))

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_lifecycle_local_main_anchor_attestation.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_scope": ANCHOR_SCOPE,
            "target_ref": TARGET_REF,
            "commit_id": self.commit_id,
            "tree_id": self.tree_id,
            "parent_commit_id": self.parent_commit_id,
            "final_preregistration_blob_id": self.final_preregistration_blob_id,
            "final_preregistration_id": self.final_preregistration_id,
            "source_registry_id": self.source_registry_id,
            "lifecycle_program_snapshot_id": self.program_snapshot_id,
            "lifecycle_program_id": self.program_id,
            "lifecycle_branch_analysis_id": self.branch_analysis_id,
            "first_qualifying_local_main_commit_verified": True,
            "single_parent_non_circular_chain_verified": True,
            "qualifying_commit_exact_single_addition_verified": True,
            "registered_component_blobs_current": True,
            "git_replace_objects_disabled": True,
            "git_object_format": "sha1",
            "snapshot_internal_semantic_replay_complete": True,
            "snapshot_dependency_semantic_binding_complete": False,
            "caller_pinned_anchor_only": True,
            "external_expected_anchor_binding_present": False,
            "worktree_execution_bytes_verified": False,
            "source_authority_present": False,
            "remote_published": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def anchor_id(self) -> str:
        if content_id(ANCHOR_DOMAIN, self._payload()) != self._anchor_id:
            _fail("local-main lifecycle anchor changed after verification")
        return self._anchor_id

    def to_document(self) -> dict[str, Any]:
        return {**self._payload(), "h1_lifecycle_local_main_anchor_id": self.anchor_id}


def verify_h1_lifecycle_local_main_anchor_v1(
    repository_root: str | Path,
) -> H1LifecycleLocalMainAnchorAttestationV1:
    """Verify K -> C and independently replay the frozen snapshot."""

    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir() or not root.joinpath(".git").exists():
        raise H1LifecycleLocalMainAnchorNotReadyV1(
            "repository root is not one Git worktree"
        )
    _verify_sha1_repository(root)
    head = _oid(str(_git(root, "rev-parse", "--verify", "HEAD")), "HEAD")
    local_main = _oid(str(_git(root, "rev-parse", "--verify", TARGET_REF)), "local main")
    if head != local_main:
        raise H1LifecycleLocalMainAnchorNotReadyV1("HEAD and local main are not identical")
    history_text = _git(root, "rev-list", "--reverse", "--topo-order", TARGET_REF)
    if type(history_text) is not str:
        _fail("local-main history is malformed")
    qualifier: tuple[str, bytes, dict[str, Any]] | None = None
    for candidate in history_text.splitlines():
        candidate_id = _oid(candidate, "history commit")
        raw = _read_blob(root, candidate_id, FINAL_PREREGISTRATION_REPOSITORY_PATH)
        if raw is not None:
            qualifier = (candidate_id, raw, _parse_final(raw))
            break
    if qualifier is None:
        raise H1LifecycleLocalMainAnchorNotReadyV1(
            "no final lifecycle preregistration exists on local main"
        )
    commit_id, final_raw, document = qualifier
    parents = _parents(root, commit_id)
    if len(parents) != 1 or parents[0] != document["expected_parent_commit_id"]:
        _fail("qualifying commit is not the single child of its registered parent")
    parent_id = parents[0]
    if _read_blob(root, parent_id, FINAL_PREREGISTRATION_REPOSITORY_PATH) is not None:
        _fail("expected parent already contains the final preregistration")
    ancestors_text = _git(root, "rev-list", parent_id)
    if type(ancestors_text) is not str:
        _fail("ancestor history is malformed")
    for ancestor in ancestors_text.splitlines():
        if _read_blob(root, ancestor, FINAL_PREREGISTRATION_REPOSITORY_PATH) is not None:
            _fail("an ancestor already contains the final preregistration")
    final_tree = _tree_blob(root, commit_id, FINAL_PREREGISTRATION_REPOSITORY_PATH)
    if final_tree is None or final_tree[0] != "100644":
        _fail("final preregistration is not one 100644 Git blob")
    _verify_exact_qualifying_diff(root, parent_id, commit_id, final_tree[1])
    _verify_components_at_commit(root, parent_id, document)
    _verify_components_at_commit(root, commit_id, document)
    _verify_components_at_commit(root, head, document)
    current_final_tree = _tree_blob(root, head, FINAL_PREREGISTRATION_REPOSITORY_PATH)
    if current_final_tree != final_tree:
        _fail("current local-main preregistration mode/blob differs from the qualifier")
    current_final = _read_blob(root, head, FINAL_PREREGISTRATION_REPOSITORY_PATH)
    if current_final is None or not hmac.compare_digest(current_final, final_raw):
        _fail("current local-main preregistration differs from the first qualifier")
    snapshot_raw = _read_blob(root, parent_id, PROGRAM_SNAPSHOT_REPOSITORY_PATH)
    if snapshot_raw is None:
        _fail("registered lifecycle program snapshot is absent")
    snapshot_id, program_id, analysis_id, transitions, branches = _verify_program_snapshot(
        snapshot_raw
    )
    if (
        snapshot_id != document["lifecycle_program_snapshot_id"]
        or program_id != document["lifecycle_program_id"]
        or analysis_id != document["lifecycle_branch_analysis_id"]
        or transitions != document["transition_count"]
        or branches != document["branch_count"]
    ):
        _fail("final preregistration differs from independent snapshot replay")
    tree_id = _oid(str(_git(root, "show", "-s", "--format=%T", commit_id)), "qualifying tree")
    if _git(root, "cat-file", "-t", tree_id) != "tree":
        _fail("qualifying tree identity is not a tree")
    return H1LifecycleLocalMainAnchorAttestationV1(
        _ANCHOR_ISSUER,
        commit_id,
        tree_id,
        parent_id,
        final_tree[1],
        document["h1_lifecycle_final_preregistration_id"],
        document["source_registry_id"],
        snapshot_id,
        program_id,
        analysis_id,
    )


@dataclass(frozen=True, slots=True)
class H1CallerPinnedLifecycleProvenanceV1:
    _issuer: InitVar[object]
    anchor_id: str
    source_registry_id: str
    program_snapshot_id: str
    program_id: str
    branch_analysis_id: str
    _provenance_id: str = field(init=False, repr=False)

    def __post_init__(self, _issuer: object) -> None:
        if _issuer is not _PROVENANCE_ISSUER:
            _fail("caller-pinned lifecycle provenance is verifier-issued only")
        for value in (
            self.anchor_id,
            self.source_registry_id,
            self.program_snapshot_id,
            self.program_id,
            self.branch_analysis_id,
        ):
            _cid(value, "caller-pinned provenance identity")
        object.__setattr__(
            self, "_provenance_id", content_id(PROVENANCE_DOMAIN, self._payload())
        )

    def _payload(self) -> dict[str, Any]:
        return {
            "schema": "acfqp.k7_h1_caller_pinned_lifecycle_provenance.v1",
            "schema_version": SCHEMA_VERSION,
            "profile_key": PROFILE_KEY,
            "anchor_scope": ANCHOR_SCOPE,
            "h1_lifecycle_local_main_anchor_id": self.anchor_id,
            "source_registry_id": self.source_registry_id,
            "lifecycle_program_snapshot_id": self.program_snapshot_id,
            "lifecycle_program_id": self.program_id,
            "lifecycle_branch_analysis_id": self.branch_analysis_id,
            "expected_anchor_id_source": "CALLER_ARGUMENT",
            "caller_pinned_anchor_only": True,
            "downstream_activation_binding_present": False,
            "worktree_component_bytes_observed_equal_once": True,
            "worktree_observation_persistent": False,
            "worktree_execution_bytes_verified": False,
            "toctou_exclusion_present": False,
            "loaded_module_bytes_verified": False,
            "execution_source_binding_present": False,
            "fresh_import_self_mint_prevented": False,
            "zero_argument_self_mint_disabled": True,
            "source_authority_present": False,
            "usable_as_execution_source": False,
            "program_status": "CALLER_PINNED_MIGRATION_SEED_ONLY",
            "remote_published": False,
            "live_dispatch_bound": False,
            "cleanup_continuation_bound": False,
            "production_execution_authorized": False,
            "official_execution_allowed": False,
        }

    @property
    def provenance_id(self) -> str:
        if content_id(PROVENANCE_DOMAIN, self._payload()) != self._provenance_id:
            _fail("caller-pinned lifecycle provenance changed after issuance")
        return self._provenance_id

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_caller_pinned_lifecycle_provenance_id": self.provenance_id,
        }


def _observe_worktree_component_bytes_once(
    root: Path, final_document: Mapping[str, Any]
) -> None:
    for row in final_document["source_registry"]["components"]:
        path = root.joinpath(row["repository_path"])
        try:
            metadata = path.lstat()
            raw = path.read_bytes()
        except OSError as error:
            raise ConstructionK7H1LifecycleLocalMainAnchorV1Error(
                "registered worktree component cannot be read"
            ) from error
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_IMODE(metadata.st_mode) & 0o111
            or len(raw) != row["byte_count"]
            or hashlib.sha256(raw).hexdigest() != row["sha256"]
        ):
            _fail("registered worktree component bytes differ from the anchor")


def inspect_h1_caller_pinned_lifecycle_provenance_v1(
    repository_root: str | Path,
    *,
    expected_anchor_id: str,
) -> H1CallerPinnedLifecycleProvenanceV1:
    """Inspect caller-pinned provenance; never return execution authority."""

    expected = _cid(expected_anchor_id, "expected lifecycle anchor")
    root = Path(repository_root).resolve(strict=True)
    anchor = verify_h1_lifecycle_local_main_anchor_v1(root)
    if not hmac.compare_digest(anchor.anchor_id, expected):
        _fail("verified local-main lifecycle anchor differs from the expected ID")
    raw = _read_blob(root, anchor.commit_id, FINAL_PREREGISTRATION_REPOSITORY_PATH)
    if raw is None:
        _fail("verified anchor lost its final preregistration")
    final_document = _parse_final(raw)
    _observe_worktree_component_bytes_once(root, final_document)
    return H1CallerPinnedLifecycleProvenanceV1(
        _PROVENANCE_ISSUER,
        anchor.anchor_id,
        anchor.source_registry_id,
        anchor.program_snapshot_id,
        anchor.program_id,
        anchor.branch_analysis_id,
    )


def official_h1_lifecycle_source_authority_v1() -> NoReturn:
    _fail(
        "zero-argument lifecycle source authority is forbidden; this contract "
        "issues caller-pinned provenance only"
    )


__all__ = (
    "ANCHOR_SCOPE",
    "ConstructionK7H1LifecycleLocalMainAnchorV1Error",
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "H1CallerPinnedLifecycleProvenanceV1",
    "H1LifecycleLocalMainAnchorAttestationV1",
    "H1LifecycleLocalMainAnchorNotReadyV1",
    "PROFILE_KEY",
    "PROGRAM_SNAPSHOT_REPOSITORY_PATH",
    "PROPOSED_CONTRACT_VERSION",
    "PROVENANCE_DOMAIN",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_REF",
    "inspect_h1_caller_pinned_lifecycle_provenance_v1",
    "official_h1_lifecycle_source_authority_v1",
    "verify_h1_lifecycle_local_main_anchor_v1",
)
