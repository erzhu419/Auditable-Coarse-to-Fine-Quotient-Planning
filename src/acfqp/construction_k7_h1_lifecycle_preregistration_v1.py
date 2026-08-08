"""Build a caller-pinned, non-circular local-Git lifecycle preregistration.

The producer reads only a pre-existing Git commit.  It binds an explicit,
non-transitive component set and a frozen declarative-program snapshot; it
does not import the module that originally produced that snapshot.  A later
single-parent commit may add the resulting JSON.  Neither commit supplies the
external activation identity or fresh-exec byte binding needed for source
authority.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path, PurePosixPath
import subprocess
from typing import Any, Mapping, NoReturn

from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN,
    CONSTRUCTION_K7_H1_LIFECYCLE_LOCAL_SOURCE_REGISTRY_V1_DOMAIN,
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
PROFILE_KEY = "construction_k7_h1_lifecycle_preregistration_v1"
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
FINAL_PREREGISTRATION_DOMAIN = (
    CONSTRUCTION_K7_H1_LIFECYCLE_FINAL_PREREGISTRATION_V1_DOMAIN
)
PROGRAM_SNAPSHOT_DOMAIN = CONSTRUCTION_K7_H1_LIFECYCLE_PROGRAM_SNAPSHOT_V1_DOMAIN
PROGRAM_DOMAIN = CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_PROGRAM_V1_DOMAIN
BRANCH_ANALYSIS_DOMAIN = (
    CONSTRUCTION_K7_H1_PRODUCTION_LIFECYCLE_BRANCH_ANALYSIS_V1_DOMAIN
)
if {
    SOURCE_REGISTRY_DOMAIN,
    FINAL_PREREGISTRATION_DOMAIN,
    PROGRAM_SNAPSHOT_DOMAIN,
    PROGRAM_DOMAIN,
    BRANCH_ANALYSIS_DOMAIN,
} - PHASE3E_DOMAIN_TAGS:  # pragma: no cover - central registry invariant
    raise RuntimeError("H1 lifecycle local-anchor domains are not registered")


# Static by design.  This is an explicit pinned boundary, not a transitive
# dependency closure and not a loaded-module closure.
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
    ("LC_ALL", "C.UTF-8"),
    ("PYTHONDONTWRITEBYTECODE", "1"),
    ("PYTHONHASHSEED", "0"),
    ("TZ", "UTC"),
)


class ConstructionK7H1LifecyclePreregistrationV1Error(ValueError):
    """The local lifecycle preregistration could not be frozen exactly."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7H1LifecyclePreregistrationV1Error(message)


def _cid(value: Any, label: str) -> str:
    try:
        return parse_content_id(value)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecyclePreregistrationV1Error(
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
        _fail("component repository path must be one nonempty string")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or str(path) != value:
        _fail("component repository path is not canonical and relative")
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
        raise ConstructionK7H1LifecyclePreregistrationV1Error(
            f"Git object query failed: {' '.join(arguments)}"
        ) from error
    if binary:
        return bytes(completed.stdout)
    try:
        return completed.stdout.decode("ascii", errors="strict").strip()
    except UnicodeDecodeError as error:
        raise ConstructionK7H1LifecyclePreregistrationV1Error(
            "Git metadata was not ASCII"
        ) from error


def _verify_sha1_repository(root: Path) -> None:
    if _git(root, "rev-parse", "--show-object-format") != "sha1":
        _fail("repository object format must be exact SHA-1")
    if _git(root, "rev-parse", "--is-shallow-repository") != "false":
        _fail("shallow repositories cannot establish first-history provenance")


@dataclass(frozen=True, slots=True)
class H1LifecycleComponentBlobV1:
    role: str
    repository_path: str
    semantic_role: str
    git_mode: str
    git_blob_id: str
    sha256: str
    byte_count: int

    def __post_init__(self) -> None:
        if (
            type(self.role) is not str
            or not self.role
            or type(self.semantic_role) is not str
            or not self.semantic_role
        ):
            _fail("component role metadata is malformed")
        _safe_path(self.repository_path)
        if self.git_mode != "100644":
            _fail("registered lifecycle components must be regular nonexecutable blobs")
        _oid(self.git_blob_id, "component blob")
        if (
            type(self.sha256) is not str
            or len(self.sha256) != 64
            or any(character not in "0123456789abcdef" for character in self.sha256)
            or type(self.byte_count) is not int
            or self.byte_count <= 0
        ):
            _fail("component digest or extent is malformed")

    def to_document(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "repository_path": self.repository_path,
            "semantic_role": self.semantic_role,
            "git_mode": self.git_mode,
            "git_blob_id": self.git_blob_id,
            "sha256": self.sha256,
            "byte_count": self.byte_count,
        }


def _component_at_commit(
    root: Path,
    commit_id: str,
    role: str,
    repository_path: str,
    semantic_role: str,
) -> H1LifecycleComponentBlobV1:
    row = _git(root, "ls-tree", commit_id, "--", repository_path)
    if type(row) is not str or not row:
        _fail(f"registered component is absent from the parent commit: {role}")
    fields = row.split(None, 3)
    if len(fields) != 4 or fields[1] != "blob" or fields[3] != repository_path:
        _fail(f"registered component tree row is malformed: {role}")
    mode, _kind, blob_id, _path = fields
    if _git(root, "cat-file", "-t", blob_id) != "blob":
        _fail(f"registered component identity is not a blob: {role}")
    raw = _git(root, "cat-file", "blob", blob_id, binary=True)
    if type(raw) is not bytes or not raw:
        _fail(f"registered component blob is empty: {role}")
    return H1LifecycleComponentBlobV1(
        role,
        repository_path,
        semantic_role,
        mode,
        blob_id,
        hashlib.sha256(raw).hexdigest(),
        len(raw),
    )


def collect_h1_lifecycle_component_registry_v1(
    repository_root: str | Path,
    *,
    commit_id: str,
) -> tuple[H1LifecycleComponentBlobV1, ...]:
    """Collect the fixed registry only from one committed Git tree."""

    root = Path(repository_root).resolve(strict=True)
    if not root.is_dir() or not root.joinpath(".git").exists():
        _fail("repository root is not one Git worktree")
    _verify_sha1_repository(root)
    selected = _oid(commit_id, "expected parent commit")
    if _git(root, "cat-file", "-t", selected) != "commit":
        _fail("expected parent identity is not a Git commit")
    rows = tuple(
        _component_at_commit(root, selected, role, path, semantic_role)
        for role, path, semantic_role in REQUIRED_COMPONENT_SPECS
    )
    if (
        tuple(row.role for row in rows)
        != tuple(row[0] for row in REQUIRED_COMPONENT_SPECS)
        or len({row.repository_path for row in rows}) != len(rows)
        or len({row.role for row in rows}) != len(rows)
    ):
        _fail("component registry is missing, reordered, or duplicated")
    return rows


def _source_registry_payload(
    components: tuple[H1LifecycleComponentBlobV1, ...],
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_lifecycle_local_source_registry.v1",
        "schema_version": SCHEMA_VERSION,
        "profile_key": PROFILE_KEY,
        "components": [row.to_document() for row in components],
        "component_count": len(components),
        "registry_is_static_not_import_inferred": True,
        "git_object_database_only": True,
        "component_set_kind": "EXPLICIT_NON_TRANSITIVE_PINNED_BOUNDARY",
        "registered_component_set_complete": True,
        "transitive_dependency_closure_verified": False,
        "loaded_module_closure_verified": False,
        "exact_test_source_bound": False,
        "semantic_source_closure_present": False,
    }


def h1_lifecycle_source_registry_id_v1(
    components: tuple[H1LifecycleComponentBlobV1, ...],
) -> str:
    return content_id(SOURCE_REGISTRY_DOMAIN, _source_registry_payload(components))


_PROGRAM_SNAPSHOT_FIELDS = frozenset(
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


def _parse_program_snapshot_reference(raw: bytes) -> tuple[str, str, str, int, int]:
    """Validate the frozen snapshot's identities without importing its producer."""

    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError) as error:
        raise ConstructionK7H1LifecyclePreregistrationV1Error(
            "lifecycle program snapshot is not canonical JSON"
        ) from error
    if type(document) is not dict or frozenset(document) != _PROGRAM_SNAPSHOT_FIELDS:
        _fail("lifecycle program snapshot fields are not exact")
    snapshot_id = _cid(
        document["h1_lifecycle_program_snapshot_id"], "program snapshot"
    )
    snapshot_payload = dict(document)
    snapshot_payload.pop("h1_lifecycle_program_snapshot_id")
    if content_id(PROGRAM_SNAPSHOT_DOMAIN, snapshot_payload) != snapshot_id:
        _fail("lifecycle program snapshot identity did not replay")
    program = document["program"]
    if type(program) is not dict:
        _fail("lifecycle program snapshot does not contain one program object")
    program_id = _cid(
        program.get("h1_production_lifecycle_program_id"), "lifecycle program"
    )
    program_payload = dict(program)
    program_payload.pop("h1_production_lifecycle_program_id", None)
    transitions = program_payload.get("transitions")
    if (
        content_id(PROGRAM_DOMAIN, program_payload) != program_id
        or type(transitions) is not list
        or program_payload.get("transition_count") != len(transitions)
        or len(transitions) != 62
        or any(type(row) is not dict for row in transitions)
    ):
        _fail("frozen lifecycle program identity or cardinality did not replay")
    branch_count = 1 + sum(
        len(row.get("failure_edges", ()))
        if type(row.get("failure_edges")) is list
        else -1000
        for row in transitions
    )
    analysis_id = _cid(document["branch_analysis_id"], "branch analysis")
    if (
        document["schema"] != "acfqp.k7_h1_lifecycle_program_snapshot.v1"
        or document["schema_version"] != SCHEMA_VERSION
        or document["proposed_contract_version"] != PROPOSED_CONTRACT_VERSION
        or document["profile_key"]
        != "construction_k7_h1_lifecycle_program_snapshot_v1"
        or document["snapshot_generation"]
        != "ONE_TIME_MIGRATION_FROM_CONTRACT_2_0_58_D"
        or document["branch_count"] != branch_count
        or branch_count != 144
        or document["program_status"] != "ANCHORED_MIGRATION_SEED_ONLY"
        or document["snapshot_is_runtime_source_authority"] is not False
        or document["production_execution_authorized"] is not False
        or document["official_execution_allowed"] is not False
    ):
        _fail("lifecycle program snapshot changed its frozen migration semantics")
    return snapshot_id, program_id, analysis_id, len(transitions), branch_count


def _final_preregistration_payload(
    *,
    expected_parent_commit_id: str,
    components: tuple[H1LifecycleComponentBlobV1, ...],
    source_registry_id: str,
    program_snapshot_id: str,
    program_id: str,
    branch_analysis_id: str,
    transition_count: int,
    branch_count: int,
) -> dict[str, Any]:
    return {
        "schema": "acfqp.k7_h1_lifecycle_final_preregistration.v1",
        "schema_version": SCHEMA_VERSION,
        "proposed_contract_version": PROPOSED_CONTRACT_VERSION,
        "profile_key": PROFILE_KEY,
        "anchor_scope": ANCHOR_SCOPE,
        "target_ref": TARGET_REF,
        "expected_parent_commit_id": expected_parent_commit_id,
        "source_registry": _source_registry_payload(components),
        "source_registry_id": source_registry_id,
        "lifecycle_program_snapshot_id": program_snapshot_id,
        "lifecycle_program_id": program_id,
        "lifecycle_branch_analysis_id": branch_analysis_id,
        "transition_count": transition_count,
        "branch_count": branch_count,
        "program_status": "CALLER_PINNED_MIGRATION_SEED_ONLY",
        "exact_test_command": list(EXACT_TEST_COMMAND),
        "deterministic_environment": [
            {"name": name, "value": value}
            for name, value in DETERMINISTIC_ENVIRONMENT
        ],
        "expected_parent_is_implementation_commit": True,
        "qualifying_commit_must_be_single_child_of_expected_parent": True,
        "first_qualifying_local_main_commit_required": True,
        "remote_published": False,
        "remote_anchor_claimed": False,
        "caller_pinned_local_git_provenance_only": True,
        "expected_anchor_id_source": "CALLER_ARGUMENT",
        "external_expected_anchor_binding_present": False,
        "zero_argument_self_mint_disabled": True,
        "fresh_import_self_mint_prevented": False,
        "source_authority_present": False,
        "execution_source_binding_present": False,
        "independent_snapshot_internal_replay_required": True,
        "snapshot_dependency_semantic_binding_complete": False,
        "component_registry_transitive_closure_complete": False,
        "live_dispatch_bound": False,
        "cleanup_continuation_bound": False,
        "production_execution_authorized": False,
        "formal_v7_route_authority_present": False,
        "counter_records_issued": False,
        "work_vector_issued": False,
        "comparison_vector_issued": False,
        "official_execution_allowed": False,
        "official_scalar_cost": None,
        "official_N_break_even": None,
        "counter_completeness_gate_status": "COUNTER_COMPLETENESS_GATE_NOT_RUN",
        "workload_economics_gate_status": "WORKLOAD_ECONOMICS_GATE_NOT_RUN",
        "sample_efficiency_gate_status": "SAMPLE_EFFICIENCY_GATE_NOT_RUN",
    }


@dataclass(frozen=True, slots=True)
class H1LifecycleFinalPreregistrationV1:
    expected_parent_commit_id: str
    components: tuple[H1LifecycleComponentBlobV1, ...]
    source_registry_id: str
    program_snapshot_id: str
    program_id: str
    branch_analysis_id: str
    transition_count: int
    branch_count: int
    _preregistration_id: str

    def __post_init__(self) -> None:
        _oid(self.expected_parent_commit_id, "expected parent commit")
        if (
            type(self.components) is not tuple
            or tuple(row.role for row in self.components)
            != tuple(row[0] for row in REQUIRED_COMPONENT_SPECS)
            or any(type(row) is not H1LifecycleComponentBlobV1 for row in self.components)
        ):
            _fail("final preregistration component registry is not exact")
        for value, label in (
            (self.source_registry_id, "source registry"),
            (self.program_snapshot_id, "program snapshot"),
            (self.program_id, "lifecycle program"),
            (self.branch_analysis_id, "branch analysis"),
            (self._preregistration_id, "final preregistration"),
        ):
            _cid(value, label)
        if self.transition_count != 62 or self.branch_count != 144:
            _fail("migration-seed lifecycle cardinalities changed")
        if h1_lifecycle_source_registry_id_v1(self.components) != self.source_registry_id:
            _fail("final preregistration source-registry identity changed")
        if content_id(FINAL_PREREGISTRATION_DOMAIN, self._payload()) != self._preregistration_id:
            _fail("final preregistration content identity changed")

    def _payload(self) -> dict[str, Any]:
        return _final_preregistration_payload(
            expected_parent_commit_id=self.expected_parent_commit_id,
            components=self.components,
            source_registry_id=self.source_registry_id,
            program_snapshot_id=self.program_snapshot_id,
            program_id=self.program_id,
            branch_analysis_id=self.branch_analysis_id,
            transition_count=self.transition_count,
            branch_count=self.branch_count,
        )

    @property
    def preregistration_id(self) -> str:
        if content_id(FINAL_PREREGISTRATION_DOMAIN, self._payload()) != self._preregistration_id:
            _fail("final preregistration changed after construction")
        return self._preregistration_id

    @property
    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_document())

    def to_document(self) -> dict[str, Any]:
        return {
            **self._payload(),
            "h1_lifecycle_final_preregistration_id": self.preregistration_id,
        }


def build_h1_lifecycle_final_preregistration_v1(
    repository_root: str | Path,
    *,
    expected_parent_commit_id: str,
) -> H1LifecycleFinalPreregistrationV1:
    """Build bytes for the later preregistration-only commit.

    The expected parent must be the current local-main HEAD.  This prevents a
    caller from quietly selecting a different historical implementation tree.
    The returned object is a preregistration document, never source authority.
    """

    root = Path(repository_root).resolve(strict=True)
    _verify_sha1_repository(root)
    selected = _oid(expected_parent_commit_id, "expected parent commit")
    head = _oid(str(_git(root, "rev-parse", "--verify", "HEAD")), "HEAD")
    local_main = _oid(str(_git(root, "rev-parse", "--verify", TARGET_REF)), "local main")
    if selected != head or selected != local_main:
        _fail("expected parent must equal HEAD and local main")
    if _git(
        root,
        "ls-tree",
        selected,
        "--",
        FINAL_PREREGISTRATION_REPOSITORY_PATH,
    ):
        _fail("implementation parent already contains a final preregistration")
    components = collect_h1_lifecycle_component_registry_v1(
        root,
        commit_id=selected,
    )
    snapshot_raw = _git(
        root,
        "show",
        f"{selected}:{PROGRAM_SNAPSHOT_REPOSITORY_PATH}",
        binary=True,
    )
    if type(snapshot_raw) is not bytes or not snapshot_raw:
        _fail("frozen lifecycle program snapshot is absent")
    (
        snapshot_id,
        program_id,
        analysis_id,
        transition_count,
        branch_count,
    ) = _parse_program_snapshot_reference(snapshot_raw)
    registry_id = h1_lifecycle_source_registry_id_v1(components)
    payload_fields = dict(
        expected_parent_commit_id=selected,
        components=components,
        source_registry_id=registry_id,
        program_snapshot_id=snapshot_id,
        program_id=program_id,
        branch_analysis_id=analysis_id,
        transition_count=transition_count,
        branch_count=branch_count,
    )
    preregistration_id = content_id(
        FINAL_PREREGISTRATION_DOMAIN,
        _final_preregistration_payload(**payload_fields),
    )
    return H1LifecycleFinalPreregistrationV1(
        **payload_fields,
        _preregistration_id=preregistration_id,
    )


def official_h1_lifecycle_source_authority_v1() -> NoReturn:
    """Fail closed: a zero-argument imported-source authority is forbidden."""

    _fail(
        "zero-argument lifecycle source authority is forbidden; verify an "
        "explicit local-main anchor ID"
    )


__all__ = (
    "ANCHOR_SCOPE",
    "ConstructionK7H1LifecyclePreregistrationV1Error",
    "DETERMINISTIC_ENVIRONMENT",
    "EXACT_TEST_COMMAND",
    "FINAL_PREREGISTRATION_REPOSITORY_PATH",
    "H1LifecycleComponentBlobV1",
    "H1LifecycleFinalPreregistrationV1",
    "PROFILE_KEY",
    "PROPOSED_CONTRACT_VERSION",
    "REQUIRED_COMPONENT_SPECS",
    "SCHEMA_VERSION",
    "TARGET_REF",
    "build_h1_lifecycle_final_preregistration_v1",
    "collect_h1_lifecycle_component_registry_v1",
    "h1_lifecycle_source_registry_id_v1",
    "official_h1_lifecycle_source_authority_v1",
)
