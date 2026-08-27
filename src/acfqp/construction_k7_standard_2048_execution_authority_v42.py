"""Committed source and one-shot execution authority for formal V42.

The prepare receipt is outcome-free.  It binds one Git commit/tree and the
complete statically imported source closure, then names one repository-fixed
authority root and one repository-fixed evidence root.  The later launch
attempt is valid only under that receipt; choosing another output directory is
not an available operation.
"""

from __future__ import annotations

import ast
import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, NoReturn

from acfqp import construction_k7_domain_registry_extension_v42 as domains
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


SCHEMA_VERSION = "42.0.0"
SOURCE_RESOLVER_VERSION = "PYTHON_STATIC_IMPORT_CLOSURE_V2"
SOURCE_CLOSURE_SCOPE = "COMMITTED_REPOSITORY_PYTHON_SOURCE_ONLY"
ALLOWED_SOURCE_GIT_MODES = ("100644",)
FORMAL_IDENTITY = "STANDARD_2048_FRESH_TERMINAL_V42_ORDINAL_1"
AUTHORITY_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_authority"
)
EVIDENCE_ROOT_RELATIVE = (
    ".tmp/exact-freeze/v42_standard_2048_fresh_terminal_execution"
)
PREPARE_RECEIPT_NAME = "PREPARE_RECEIPT.json"
PREPARE_ATTEMPT_JOURNAL_NAME = ".V42_FRESH_TERMINAL_PREPARE_ATTEMPT.json"
PREPARE_FAILURE_JOURNAL_NAME = ".V42_FRESH_TERMINAL_PREPARE_FAILURE.json"
LAUNCH_ATTEMPT_JOURNAL_NAME = ".V42_FRESH_TERMINAL_LAUNCH_ATTEMPT.json"
LAUNCH_FAILURE_JOURNAL_NAME = ".V42_FRESH_TERMINAL_LAUNCH_FAILURE.json"
ATTEMPT_NAME = "ATTEMPT.json"
WORKER_START_NAME = "WORKER_START.json"
AUTHORITY_CONSUMPTION_NAME = "AUTHORITY_CONSUMPTION.json"
CAMPAIGN_NAME = "CAMPAIGN.json"
VERIFICATION_NAME = "VERIFICATION.json"
TERMINAL_NAME = "TERMINAL.json"
FAILURE_NAME = "FAILURE.json"

FORMAL_SOURCE_ROOTS = (
    "src/acfqp/construction_k7_domain_registry_extension_v42.py",
    "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
    "src/acfqp/construction_k7_standard_2048_execution_authority_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_campaign_v42.py",
    "src/acfqp/construction_k7_standard_2048_fresh_terminal_independent_verifier_v42.py",
    "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
    "src/acfqp/construction_k7_standard_2048_observation_proposed_program_v14.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
    "src/acfqp/construction_k7_standard_2048_adaptive_expression_independent_verifier_v35.py",
    "src/acfqp/construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14.py",
    "src/acfqp/domains/standard_2048.py",
    "src/acfqp/domains/g2048.py",
    "scripts/run_v42_standard_2048_fresh_terminal_campaign.py",
    "scripts/supervise_v42_standard_2048_fresh_terminal_campaign.py",
)
REQUIRED_FROZEN_SEMANTIC_SOURCE_FACTS = (
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_expression_planner_v1.py",
        "byte_count": 15_747,
        "sha256": "c2f06fcd78e41683544d243d23a4bdb5891b0523fbaa84ce771614c551f0aae2",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_adaptive_expression_target_v35.py",
        "byte_count": 3_853,
        "sha256": "3cc08eb7c86008e236205f2a1f48dcd8189ebb97f7c210312794c0f703b4c17b",
    },
    {
        "relative_path": "src/acfqp/domains/standard_2048.py",
        "byte_count": 14_739,
        "sha256": "0fabdec281cc94c53bceef37bdb5336da45c71c7339370d25d7dfa076aa7154c",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_observation_proposed_program_v14.py",
        "byte_count": 21_874,
        "sha256": "8dffde09e527d10027b4467323b4d8d35e4398c7ddad153e76cc5b830c02092e",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_observation_proposed_program_independent_verifier_v14.py",
        "byte_count": 20_452,
        "sha256": "74fe6af1f77dfd219eabf502fbd750c6ad9b6da1ba93d3f0365e8f447e93dc91",
    },
    {
        "relative_path": "src/acfqp/domains/g2048.py",
        "byte_count": 19_366,
        "sha256": "193ba8b50658a2a6d49baf964b409fbc45891f447af0d56ebda5b7d2a63596bf",
    },
    {
        "relative_path": "src/acfqp/construction_k7_standard_2048_adaptive_expression_independent_verifier_v35.py",
        "byte_count": 61_787,
        "sha256": "4605a6ee16cf3cbc5b6d0409dbf0ef506f4fac7ecae79d474aea0987ed97bbbe",
    },
)

_HEX40_OR_64 = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})")
_HEX64 = re.compile(r"[0-9a-f]{64}")
_SOURCE_MANIFEST_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "resolver_version",
        "source_commit",
        "source_tree",
        "source_roots",
        "source_closure_scope",
        "stdlib_and_interpreter_sources_excluded",
        "external_python_distributions_excluded",
        "non_python_resources_excluded",
        "allowed_source_git_modes",
        "unresolved_dynamic_import_sites_runtime_guarded",
        "source_path_count",
        "source_facts",
        "dynamic_import_sites",
        "source_manifest_id",
    }
)
_SOURCE_FACT_FIELDS = frozenset(
    {
        "relative_path",
        "git_mode",
        "git_object_type",
        "git_blob_id",
        "byte_count",
        "sha256",
    }
)
_PREPARE_RECEIPT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "fresh_terminal_preregistration_id",
        "history_freshness_manifest_id",
        "source_commit",
        "source_tree",
        "source_manifest",
        "source_manifest_id",
        "authority_root_relative",
        "evidence_root_relative",
        "launch_ordinal",
        "outcome_or_tape_materialized",
        "formal_execution_performed",
        "prepare_receipt_id",
    }
)
_ATTEMPT_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "prepare_receipt_id",
        "fresh_terminal_preregistration_id",
        "history_freshness_manifest_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "attempt_ordinal",
        "registered_episode_count",
        "decision_index_starts_at",
        "decision_cap_per_episode",
        "fixed_evidence_root_relative",
        "same_identity_rerun_forbidden",
        "outcome_fields_present",
        "runner_attempt_id",
    }
)
_WORKER_START_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "prepare_receipt_id",
        "runner_attempt_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "worker_start_ordinal",
        "worker_authorization_secret_sha256",
        "producer_process_isolated",
        "verifier_process_isolated",
        "isolated_python_flags",
        "same_identity_worker_restart_forbidden",
        "outcome_fields_present",
        "worker_start_id",
    }
)
_AUTHORITY_CONSUMPTION_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "formal_identity",
        "prepare_receipt_id",
        "runner_attempt_id",
        "worker_start_id",
        "worker_authorization_secret_sha256",
        "consumption_ordinal",
        "consumed_by_role",
        "same_identity_authority_reissue_forbidden",
        "outcome_fields_present",
        "authority_consumption_id",
    }
)
_SOURCE_BINDING_FIELDS = frozenset(
    {
        "schema",
        "schema_version",
        "prepare_receipt_id",
        "runner_attempt_id",
        "worker_start_id",
        "authority_consumption_id",
        "source_commit",
        "source_tree",
        "source_manifest_id",
        "fresh_terminal_preregistration_id",
        "target_kernel_id",
        "adaptive_expression_overlay_id",
        "adaptive_expression_proof_id",
        "adaptive_expression_model_id",
        "planner_id",
        "binding_frozen_before_first_registered_target_transition",
        "source_binding_id",
    }
)


class ConstructionK7Standard2048ExecutionAuthorityV42Error(ValueError):
    """The source closure, receipt, attempt, or fixed identity changed."""


def _fail(message: str) -> NoReturn:
    raise ConstructionK7Standard2048ExecutionAuthorityV42Error(message)


def _git(root: Path, *arguments: str, allow_failure: bool = False) -> bytes:
    completed = subprocess.run(
        ("git", *arguments),
        cwd=root,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if completed.returncode != 0 and not allow_failure:
        _fail(
            f"git {' '.join(arguments)} failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return completed.stdout if completed.returncode == 0 else b""


def _canonical_document(raw_or_document: bytes | dict[str, Any], label: str) -> dict[str, Any]:
    if type(raw_or_document) is bytes:
        try:
            document = loads_canonical_json(raw_or_document)
        except (TypeError, ValueError) as error:
            raise ConstructionK7Standard2048ExecutionAuthorityV42Error(
                f"{label} is not canonical JSON"
            ) from error
        if type(document) is not dict or canonical_json_bytes(document) != raw_or_document:
            _fail(f"{label} canonical bytes changed")
        return document
    if type(raw_or_document) is not dict:
        _fail(f"{label} is not an object")
    # Round-trip rejects unsupported or noncanonical value types.
    raw = canonical_json_bytes(raw_or_document)
    document = loads_canonical_json(raw)
    if type(document) is not dict or document != raw_or_document:
        _fail(f"{label} values changed under canonical encoding")
    return document


def _commit_path_exists(root: Path, commit: str, relative_path: str) -> bool:
    completed = subprocess.run(
        ("git", "cat-file", "-e", f"{commit}:{relative_path}"),
        cwd=root,
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def _module_candidates(name: str) -> set[str]:
    """Return module and package candidates, including parent packages."""

    if name == "acfqp" or name.startswith("acfqp."):
        prefix = "src/"
    elif name == "scripts" or name.startswith("scripts."):
        prefix = ""
    else:
        return set()
    parts = name.split(".")
    candidates = {
        prefix + "/".join(parts) + ".py",
        prefix + "/".join(parts) + "/__init__.py",
    }
    for limit in range(1, len(parts)):
        candidates.add(prefix + "/".join(parts[:limit]) + "/__init__.py")
    return candidates


def _relative_module_candidates(current_path: str, level: int, module: str) -> set[str]:
    current = PurePosixPath(current_path)
    package = current.parent
    for _ in range(max(level - 1, 0)):
        package = package.parent
    target = package / module.replace(".", "/") if module else package
    candidates = {str(target) + ".py", str(target / "__init__.py")}
    parent = target.parent
    while str(parent).startswith("src/acfqp") and str(parent) != "src":
        candidates.add(str(parent / "__init__.py"))
        parent = parent.parent
    return candidates


def _resolve_import_candidates(
    tree: ast.AST, *, current_path: str
) -> tuple[set[str], list[dict[str, Any]]]:
    candidates: set[str] = set()
    dynamic: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                candidates.update(_module_candidates(alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                candidates.update(
                    _relative_module_candidates(current_path, node.level, module)
                )
                for alias in node.names:
                    if alias.name != "*":
                        child = f"{module}.{alias.name}" if module else alias.name
                        candidates.update(
                            _relative_module_candidates(current_path, node.level, child)
                        )
            elif module == "acfqp" or module.startswith("acfqp."):
                candidates.update(_module_candidates(module))
                for alias in node.names:
                    if alias.name != "*":
                        candidates.update(_module_candidates(module + "." + alias.name))
            elif module == "scripts" or module.startswith("scripts."):
                candidates.update(_module_candidates(module))
                for alias in node.names:
                    if alias.name != "*":
                        candidates.update(_module_candidates(module + "." + alias.name))
        elif isinstance(node, ast.Call):
            name = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
            elif isinstance(node.func, ast.Attribute):
                name = node.func.attr
            if name in {"__import__", "import_module"}:
                dynamic.append({"relative_path": current_path, "line": node.lineno, "call": name})
    return candidates, dynamic


def _tree_entries_for_paths(
    root: Path, commit: str, relative_paths: Iterable[str]
) -> dict[str, dict[str, str]]:
    paths = tuple(sorted(set(relative_paths)))
    if not paths:
        _fail("source closure tree lookup is empty")
    raw = _git(
        root,
        "ls-tree",
        "-z",
        "--full-tree",
        commit,
        "--",
        *(f":(literal){path}" for path in paths),
    )
    entries: dict[str, dict[str, str]] = {}
    for record in raw.split(b"\0"):
        if not record:
            continue
        try:
            metadata, raw_path = record.split(b"\t", 1)
            mode, object_type, object_id = metadata.decode("ascii").split(" ")
            path = raw_path.decode("utf-8")
        except (UnicodeDecodeError, ValueError) as error:
            raise ConstructionK7Standard2048ExecutionAuthorityV42Error(
                "committed source ls-tree record is malformed"
            ) from error
        if path in entries:
            _fail("committed source ls-tree repeated a path")
        entries[path] = {
            "git_mode": mode,
            "git_object_type": object_type,
            "git_blob_id": object_id,
        }
    if set(entries) != set(paths):
        _fail("committed source grouped ls-tree inventory changed")
    for path, entry in entries.items():
        if (
            entry["git_mode"] not in ALLOWED_SOURCE_GIT_MODES
            or entry["git_object_type"] != "blob"
            or _HEX40_OR_64.fullmatch(entry["git_blob_id"]) is None
        ):
            _fail(f"committed source is not an allowed regular Python blob: {path}")
    return entries


def build_source_manifest_from_commit_v42(
    root: Path,
    *,
    source_commit: str,
    source_roots: tuple[str, ...] = FORMAL_SOURCE_ROOTS,
) -> dict[str, Any]:
    """Independently resolve and hash the committed transitive Python closure."""

    root = root.resolve()
    if type(source_commit) is not str or _HEX40_OR_64.fullmatch(source_commit) is None:
        _fail("source manifest requires one full lowercase commit")
    resolved_commit = _git(root, "rev-parse", "--verify", f"{source_commit}^{{commit}}").decode("ascii").strip()
    if resolved_commit != source_commit:
        _fail("source manifest commit is abbreviated or changed")
    source_tree = _git(root, "rev-parse", f"{source_commit}^{{tree}}").decode("ascii").strip()
    pending = list(source_roots)
    visited: set[str] = set()
    dynamic_sites: list[dict[str, Any]] = []
    source_bytes: dict[str, bytes] = {}
    while pending:
        relative_path = pending.pop()
        if relative_path in visited:
            continue
        if (
            PurePosixPath(relative_path).is_absolute()
            or ".." in PurePosixPath(relative_path).parts
            or not relative_path.endswith(".py")
        ):
            _fail("source closure path is not one repository-relative Python file")
        if not _commit_path_exists(root, source_commit, relative_path):
            _fail(f"committed source root or dependency is absent: {relative_path}")
        tree_entry = _tree_entries_for_paths(root, source_commit, (relative_path,))[
            relative_path
        ]
        visited.add(relative_path)
        raw = _git(root, "cat-file", "blob", tree_entry["git_blob_id"])
        source_bytes[relative_path] = raw
        try:
            parsed = ast.parse(raw.decode("utf-8"), filename=relative_path)
        except (UnicodeDecodeError, SyntaxError) as error:
            raise ConstructionK7Standard2048ExecutionAuthorityV42Error(
                f"committed Python source cannot be parsed: {relative_path}"
            ) from error
        imported, dynamic = _resolve_import_candidates(parsed, current_path=relative_path)
        dynamic_sites.extend(dynamic)
        for candidate in sorted(imported):
            if _commit_path_exists(root, source_commit, candidate):
                pending.append(candidate)
    grouped_entries = _tree_entries_for_paths(root, source_commit, visited)
    facts = [
        {
            "relative_path": relative_path,
            **grouped_entries[relative_path],
            "byte_count": len(source_bytes[relative_path]),
            "sha256": hashlib.sha256(source_bytes[relative_path]).hexdigest(),
        }
        for relative_path in sorted(visited)
    ]
    facts.sort(key=lambda row: row["relative_path"])
    dynamic_sites.sort(key=lambda row: (row["relative_path"], row["line"], row["call"]))
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_source_manifest.v42",
        "schema_version": SCHEMA_VERSION,
        "resolver_version": SOURCE_RESOLVER_VERSION,
        "source_commit": source_commit,
        "source_tree": source_tree,
        "source_roots": list(source_roots),
        "source_closure_scope": SOURCE_CLOSURE_SCOPE,
        "stdlib_and_interpreter_sources_excluded": True,
        "external_python_distributions_excluded": True,
        "non_python_resources_excluded": True,
        "allowed_source_git_modes": list(ALLOWED_SOURCE_GIT_MODES),
        "unresolved_dynamic_import_sites_runtime_guarded": True,
        "source_path_count": len(facts),
        "source_facts": facts,
        "dynamic_import_sites": dynamic_sites,
    }
    return {
        **payload,
        "source_manifest_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_SOURCE_MANIFEST_V42_DOMAIN, payload
        ),
    }


def verify_source_manifest_document_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    root: Path | None = None,
    recompute_from_commit: bool = False,
    source_roots: tuple[str, ...] = FORMAL_SOURCE_ROOTS,
    enforce_frozen_semantic_sources: bool = True,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 source manifest")
    if set(document) != _SOURCE_MANIFEST_FIELDS:
        _fail("V42 source manifest schema is not exact")
    payload = {key: value for key, value in document.items() if key != "source_manifest_id"}
    if (
        document.get("schema")
        != "acfqp.standard_2048_fresh_terminal_source_manifest.v42"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("resolver_version") != SOURCE_RESOLVER_VERSION
        or type(document.get("source_commit")) is not str
        or _HEX40_OR_64.fullmatch(document["source_commit"]) is None
        or type(document.get("source_tree")) is not str
        or _HEX40_OR_64.fullmatch(document["source_tree"]) is None
        or document.get("source_roots") != list(source_roots)
        or document.get("source_closure_scope") != SOURCE_CLOSURE_SCOPE
        or document.get("stdlib_and_interpreter_sources_excluded") is not True
        or document.get("external_python_distributions_excluded") is not True
        or document.get("non_python_resources_excluded") is not True
        or document.get("allowed_source_git_modes") != list(ALLOWED_SOURCE_GIT_MODES)
        or document.get("unresolved_dynamic_import_sites_runtime_guarded") is not True
        or type(document.get("source_path_count")) is not int
        or type(document.get("source_manifest_id")) is not str
        or _HEX64.fullmatch(document["source_manifest_id"]) is None
        or domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_SOURCE_MANIFEST_V42_DOMAIN, payload
        )
        != document["source_manifest_id"]
    ):
        _fail("V42 source manifest semantics or identity changed")
    dynamic_sites = document.get("dynamic_import_sites")
    if type(dynamic_sites) is not list:
        _fail("V42 source manifest dynamic-import inventory changed")
    previous_dynamic_key: tuple[str, int, str] | None = None
    for site in dynamic_sites:
        if (
            type(site) is not dict
            or set(site) != {"relative_path", "line", "call"}
            or type(site.get("relative_path")) is not str
            or type(site.get("line")) is not int
            or site["line"] <= 0
            or site.get("call") not in {"__import__", "import_module"}
        ):
            _fail("V42 source manifest dynamic-import site changed")
        dynamic_key = (site["relative_path"], site["line"], site["call"])
        if previous_dynamic_key is not None and dynamic_key <= previous_dynamic_key:
            _fail("V42 source manifest dynamic-import sites are not sorted and unique")
        previous_dynamic_key = dynamic_key
    facts = document.get("source_facts")
    if type(facts) is not list or len(facts) != document["source_path_count"] or not facts:
        _fail("V42 source manifest fact inventory changed")
    paths: list[str] = []
    for fact in facts:
        if (
            type(fact) is not dict
            or set(fact) != _SOURCE_FACT_FIELDS
            or type(fact.get("relative_path")) is not str
            or PurePosixPath(fact["relative_path"]).is_absolute()
            or ".." in PurePosixPath(fact["relative_path"]).parts
            or not fact["relative_path"].endswith(".py")
            or fact.get("git_mode") not in ALLOWED_SOURCE_GIT_MODES
            or fact.get("git_object_type") != "blob"
            or type(fact.get("git_blob_id")) is not str
            or _HEX40_OR_64.fullmatch(fact["git_blob_id"]) is None
            or type(fact.get("byte_count")) is not int
            or fact["byte_count"] <= 0
            or type(fact.get("sha256")) is not str
            or _HEX64.fullmatch(fact["sha256"]) is None
        ):
            _fail("V42 source manifest fact changed")
        paths.append(fact["relative_path"])
    if paths != sorted(paths) or len(set(paths)) != len(paths):
        _fail("V42 source manifest paths are not sorted and unique")
    if not set(source_roots) <= set(paths):
        _fail("V42 source manifest omitted an explicit formal source root")
    if any(site["relative_path"] not in set(paths) for site in dynamic_sites):
        _fail("V42 dynamic-import site is outside the source fact closure")
    by_path = {fact["relative_path"]: fact for fact in facts}
    if enforce_frozen_semantic_sources:
        for required in REQUIRED_FROZEN_SEMANTIC_SOURCE_FACTS:
            observed = by_path.get(required["relative_path"])
            if observed is None or {
                "relative_path": observed["relative_path"],
                "byte_count": observed["byte_count"],
                "sha256": observed["sha256"],
            } != required:
                _fail(
                    "V42 committed semantic source differs from the frozen model/planner closure: "
                    + required["relative_path"]
                )
    if recompute_from_commit:
        if root is None:
            _fail("V42 source manifest recomputation requires a repository root")
        expected = build_source_manifest_from_commit_v42(
            root,
            source_commit=document["source_commit"],
            source_roots=source_roots,
        )
        if document != expected:
            _fail("V42 source manifest differs from independent commit-tree replay")
    return document


def _read_regular_nofollow_stable(path: Path) -> tuple[bytes, os.stat_result]:
    """Read one live source without following links or accepting a racing inode."""

    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        _fail(f"live source is not a regular file: {path}")
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    try:
        opened = os.fstat(descriptor)
        if (
            not stat.S_ISREG(opened.st_mode)
            or (before.st_dev, before.st_ino, before.st_mode, before.st_size)
            != (opened.st_dev, opened.st_ino, opened.st_mode, opened.st_size)
        ):
            _fail(f"live source changed while opening: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after_read = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    after_close = path.lstat()
    stable_fields = ("st_dev", "st_ino", "st_mode", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(opened, name) != getattr(after_read, name)
        or getattr(opened, name) != getattr(after_close, name)
        for name in stable_fields
    ):
        _fail(f"live source changed during stable read: {path}")
    return b"".join(chunks), after_read


def verify_live_source_matches_manifest_v42(
    root: Path,
    manifest: dict[str, Any],
    *,
    source_roots: tuple[str, ...] = FORMAL_SOURCE_ROOTS,
    enforce_frozen_semantic_sources: bool = True,
) -> None:
    manifest = verify_source_manifest_document_v42(
        manifest,
        source_roots=source_roots,
        enforce_frozen_semantic_sources=enforce_frozen_semantic_sources,
    )
    root = root.resolve()
    head = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    if head != manifest["source_commit"]:
        _fail("live HEAD differs from the prepared V42 source commit")
    paths = tuple(fact["relative_path"] for fact in manifest["source_facts"])
    status = _git(
        root,
        "status",
        "--porcelain=v1",
        "--untracked-files=all",
        "--",
        *paths,
    ).decode("utf-8", errors="replace")
    if status:
        _fail("live V42 transitive source closure differs from prepared HEAD")
    for fact in manifest["source_facts"]:
        path = root / fact["relative_path"]
        raw, observed = _read_regular_nofollow_stable(path)
        executable = bool(stat.S_IMODE(observed.st_mode) & 0o111)
        if fact["git_mode"] == "100644" and executable:
            _fail(f"live source executable mode changed: {fact['relative_path']}")
        if len(raw) != fact["byte_count"] or hashlib.sha256(raw).hexdigest() != fact["sha256"]:
            _fail(f"live source bytes changed: {fact['relative_path']}")


def verify_runtime_repository_modules_in_manifest_v42(
    root: Path,
    manifest: dict[str, Any],
    *,
    source_roots: tuple[str, ...] = FORMAL_SOURCE_ROOTS,
    enforce_frozen_semantic_sources: bool = True,
) -> tuple[str, ...]:
    """Reject any repository module loaded outside the committed closure.

    This is the execution-time complement to the conservative static resolver:
    variable-driven import sites are frozen in the manifest, and no such site
    may cause an unmanifested repository module to enter ``sys.modules``.
    """

    manifest = verify_source_manifest_document_v42(
        manifest,
        source_roots=source_roots,
        enforce_frozen_semantic_sources=enforce_frozen_semantic_sources,
    )
    root = root.resolve()
    allowed = {fact["relative_path"] for fact in manifest["source_facts"]}
    observed: set[str] = set()
    for module in tuple(sys.modules.values()):
        raw_file = getattr(module, "__file__", None)
        if type(raw_file) is not str:
            continue
        try:
            path = Path(raw_file).resolve(strict=True)
            relative = path.relative_to(root).as_posix()
        except (FileNotFoundError, OSError, ValueError):
            continue
        if relative.endswith((".pyc", ".pyo")):
            _fail(f"isolated V42 runtime loaded repository bytecode: {relative}")
        if relative not in allowed:
            _fail(f"isolated V42 runtime loaded unmanifested repository module: {relative}")
        observed.add(relative)
    return tuple(sorted(observed))


class _ManifestRepositoryImportGuardV42:
    def __init__(self, root: Path, allowed: frozenset[str]) -> None:
        self._root = root
        self._allowed = allowed

    def find_spec(self, fullname: str, path: Any = None, target: Any = None) -> None:
        del path, target
        if fullname == "acfqp" or fullname.startswith("acfqp."):
            base = self._root / "src" / Path(*fullname.split("."))
        elif fullname == "scripts" or fullname.startswith("scripts."):
            base = self._root / Path(*fullname.split("."))
        else:
            return None
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            try:
                relative = candidate.relative_to(self._root).as_posix()
                present = candidate.lstat()
            except FileNotFoundError:
                continue
            if not stat.S_ISREG(present.st_mode) or relative not in self._allowed:
                _fail(
                    "isolated V42 import guard rejected an unmanifested repository module: "
                    + relative
                )
        return None


def install_runtime_repository_import_guard_v42(
    root: Path,
    manifest: dict[str, Any],
    *,
    source_roots: tuple[str, ...] = FORMAL_SOURCE_ROOTS,
    enforce_frozen_semantic_sources: bool = True,
) -> object:
    """Install a pre-loader guard against dynamic repository dependencies."""

    manifest = verify_source_manifest_document_v42(
        manifest,
        source_roots=source_roots,
        enforce_frozen_semantic_sources=enforce_frozen_semantic_sources,
    )
    guard = _ManifestRepositoryImportGuardV42(
        root.resolve(),
        frozenset(fact["relative_path"] for fact in manifest["source_facts"]),
    )
    sys.meta_path.insert(0, guard)
    return guard


def build_prepare_receipt_v42(
    root: Path,
    *,
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
) -> dict[str, Any]:
    root = root.resolve()
    head = _git(root, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    manifest = build_source_manifest_from_commit_v42(root, source_commit=head)
    verify_live_source_matches_manifest_v42(root, manifest)
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_prepare_receipt.v42",
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "fresh_terminal_preregistration_id": fresh_terminal_preregistration_id,
        "history_freshness_manifest_id": history_freshness_manifest_id,
        "source_commit": manifest["source_commit"],
        "source_tree": manifest["source_tree"],
        "source_manifest": manifest,
        "source_manifest_id": manifest["source_manifest_id"],
        "authority_root_relative": AUTHORITY_ROOT_RELATIVE,
        "evidence_root_relative": EVIDENCE_ROOT_RELATIVE,
        "launch_ordinal": 1,
        "outcome_or_tape_materialized": False,
        "formal_execution_performed": False,
    }
    return {
        **payload,
        "prepare_receipt_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_PREPARE_RECEIPT_V42_DOMAIN, payload
        ),
    }


def verify_prepare_receipt_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    root: Path | None = None,
    require_live_source: bool = False,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 prepare receipt")
    if set(document) != _PREPARE_RECEIPT_FIELDS:
        _fail("V42 prepare receipt schema is not exact")
    payload = {key: value for key, value in document.items() if key != "prepare_receipt_id"}
    manifest = verify_source_manifest_document_v42(
        document.get("source_manifest"),
        root=root,
        recompute_from_commit=require_live_source,
    )
    if (
        document.get("schema")
        != "acfqp.standard_2048_fresh_terminal_prepare_receipt.v42"
        or document.get("schema_version") != SCHEMA_VERSION
        or document.get("formal_identity") != FORMAL_IDENTITY
        or document.get("fresh_terminal_preregistration_id")
        != fresh_terminal_preregistration_id
        or document.get("history_freshness_manifest_id")
        != history_freshness_manifest_id
        or document.get("source_commit") != manifest["source_commit"]
        or document.get("source_tree") != manifest["source_tree"]
        or document.get("source_manifest_id") != manifest["source_manifest_id"]
        or document.get("authority_root_relative") != AUTHORITY_ROOT_RELATIVE
        or document.get("evidence_root_relative") != EVIDENCE_ROOT_RELATIVE
        or document.get("launch_ordinal") != 1
        or document.get("outcome_or_tape_materialized") is not False
        or document.get("formal_execution_performed") is not False
        or domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_PREPARE_RECEIPT_V42_DOMAIN, payload
        )
        != document.get("prepare_receipt_id")
    ):
        _fail("V42 prepare receipt semantics or identity changed")
    if require_live_source:
        if root is None:
            _fail("live prepare verification requires a repository root")
        verify_live_source_matches_manifest_v42(root, manifest)
    return document


def build_runner_attempt_v42(
    prepare_receipt: dict[str, Any],
    *,
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_runner_attempt.v42",
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "fresh_terminal_preregistration_id": prepare_receipt[
            "fresh_terminal_preregistration_id"
        ],
        "history_freshness_manifest_id": prepare_receipt[
            "history_freshness_manifest_id"
        ],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "attempt_ordinal": 1,
        "registered_episode_count": registered_episode_count,
        "decision_index_starts_at": 0,
        "decision_cap_per_episode": decision_cap_per_episode,
        "fixed_evidence_root_relative": EVIDENCE_ROOT_RELATIVE,
        "same_identity_rerun_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "runner_attempt_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_RUNNER_ATTEMPT_V42_DOMAIN, payload
        ),
    }


def verify_runner_attempt_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    prepare_receipt: dict[str, Any],
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 runner attempt")
    if set(document) != _ATTEMPT_FIELDS:
        _fail("V42 runner attempt schema is not exact")
    expected = build_runner_attempt_v42(
        prepare_receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
    )
    if document != expected:
        _fail("V42 runner attempt differs from its committed prepare authority")
    return document


def build_worker_start_v42(
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_authorization_secret_sha256: str,
) -> dict[str, Any]:
    if (
        type(worker_authorization_secret_sha256) is not str
        or _HEX64.fullmatch(worker_authorization_secret_sha256) is None
    ):
        _fail("V42 worker authorization hash changed")
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_worker_start.v42",
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "worker_start_ordinal": 1,
        "worker_authorization_secret_sha256": worker_authorization_secret_sha256,
        "producer_process_isolated": True,
        "verifier_process_isolated": True,
        "isolated_python_flags": ["-I", "-S", "-B"],
        "same_identity_worker_restart_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "worker_start_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_WORKER_START_V42_DOMAIN, payload
        ),
    }


def verify_worker_start_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_authorization_secret_sha256: str,
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 worker start")
    if set(document) != _WORKER_START_FIELDS:
        _fail("V42 worker start schema is not exact")
    expected = build_worker_start_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_authorization_secret_sha256=worker_authorization_secret_sha256,
    )
    if document != expected:
        _fail("V42 worker start differs from supervisor-issued authorization")
    return document


def build_authority_consumption_v42(
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_authority_consumption.v42",
        "schema_version": SCHEMA_VERSION,
        "formal_identity": FORMAL_IDENTITY,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "worker_authorization_secret_sha256": worker_start[
            "worker_authorization_secret_sha256"
        ],
        "consumption_ordinal": 1,
        "consumed_by_role": "ISOLATED_FRESH_PRODUCER_PROCESS",
        "same_identity_authority_reissue_forbidden": True,
        "outcome_fields_present": False,
    }
    return {
        **payload,
        "authority_consumption_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_AUTHORITY_CONSUMPTION_V42_DOMAIN, payload
        ),
    }


def verify_authority_consumption_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 authority consumption")
    if set(document) != _AUTHORITY_CONSUMPTION_FIELDS:
        _fail("V42 authority consumption schema is not exact")
    expected = build_authority_consumption_v42(
        prepare_receipt=prepare_receipt,
        runner_attempt=runner_attempt,
        worker_start=worker_start,
    )
    if document != expected:
        _fail("V42 authority consumption differs from worker authorization")
    return document


def _write_authority_artifact_once(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | os.O_NOFOLLOW
        | os.O_CLOEXEC,
        0o400,
    )
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("V42 authority consumption short write")
            view = view[written:]
        os.fchmod(descriptor, 0o400)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    retained, observed = _read_regular_nofollow_stable(path)
    if retained != raw or stat.S_IMODE(observed.st_mode) != 0o400:
        _fail("V42 authority consumption durable readback changed")
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def consume_supervisor_worker_authorization_v42(
    root: Path,
    *,
    worker_authorization_secret: bytes,
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    """Atomically consume the fixed supervisor authorization exactly once."""

    if type(worker_authorization_secret) is not bytes or len(worker_authorization_secret) != 32:
        _fail("V42 producer did not receive one 256-bit supervisor secret")
    authority_root = fixed_authority_root_v42(root)
    evidence_root = fixed_evidence_root_v42(root)
    receipt_bytes, _ = _read_regular_nofollow_stable(
        authority_root / PREPARE_RECEIPT_NAME
    )
    attempt_bytes, _ = _read_regular_nofollow_stable(evidence_root / ATTEMPT_NAME)
    receipt = verify_prepare_receipt_v42(
        receipt_bytes,
        fresh_terminal_preregistration_id=fresh_terminal_preregistration_id,
        history_freshness_manifest_id=history_freshness_manifest_id,
        root=root,
        require_live_source=True,
    )
    attempt = verify_runner_attempt_v42(
        attempt_bytes,
        prepare_receipt=receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
    )
    worker_start_bytes, _ = _read_regular_nofollow_stable(
        evidence_root / WORKER_START_NAME
    )
    secret_sha256 = hashlib.sha256(worker_authorization_secret).hexdigest()
    worker_start = verify_worker_start_v42(
        worker_start_bytes,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256=secret_sha256,
    )
    verify_live_source_matches_manifest_v42(root, receipt["source_manifest"])
    consumption = build_authority_consumption_v42(
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=worker_start,
    )
    _write_authority_artifact_once(
        evidence_root / AUTHORITY_CONSUMPTION_NAME,
        canonical_json_bytes(consumption),
    )
    return receipt, attempt, worker_start, consumption


def verify_consumed_formal_authority_v42(
    root: Path,
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
    authority_consumption: dict[str, Any],
    fresh_terminal_preregistration_id: str,
    history_freshness_manifest_id: str,
    registered_episode_count: int,
    decision_cap_per_episode: int,
) -> None:
    """Rejoin an issued capability to every exact fixed durable artifact."""

    authority_root = fixed_authority_root_v42(root)
    evidence_root = fixed_evidence_root_v42(root)
    expected_documents = (
        (authority_root / PREPARE_RECEIPT_NAME, prepare_receipt, "prepare receipt"),
        (evidence_root / ATTEMPT_NAME, runner_attempt, "runner attempt"),
        (evidence_root / WORKER_START_NAME, worker_start, "worker start"),
        (
            evidence_root / AUTHORITY_CONSUMPTION_NAME,
            authority_consumption,
            "authority consumption",
        ),
    )
    for path, expected, label in expected_documents:
        raw, _ = _read_regular_nofollow_stable(path)
        if raw != canonical_json_bytes(expected):
            _fail(f"fixed durable V42 {label} bytes changed")
    receipt = verify_prepare_receipt_v42(
        prepare_receipt,
        fresh_terminal_preregistration_id=fresh_terminal_preregistration_id,
        history_freshness_manifest_id=history_freshness_manifest_id,
        root=root,
        require_live_source=True,
    )
    attempt = verify_runner_attempt_v42(
        runner_attempt,
        prepare_receipt=receipt,
        registered_episode_count=registered_episode_count,
        decision_cap_per_episode=decision_cap_per_episode,
    )
    verified_worker = verify_worker_start_v42(
        worker_start,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_authorization_secret_sha256=worker_start[
            "worker_authorization_secret_sha256"
        ],
    )
    verify_authority_consumption_v42(
        authority_consumption,
        prepare_receipt=receipt,
        runner_attempt=attempt,
        worker_start=verified_worker,
    )
    verify_live_source_matches_manifest_v42(root, receipt["source_manifest"])


def build_campaign_source_binding_v42(
    *,
    prepare_receipt: dict[str, Any],
    runner_attempt: dict[str, Any],
    worker_start: dict[str, Any],
    authority_consumption: dict[str, Any],
    fresh_terminal_preregistration_id: str,
    target_kernel_id: str,
    adaptive_expression_overlay_id: str,
    adaptive_expression_proof_id: str,
    adaptive_expression_model_id: str,
    planner_id: str,
) -> dict[str, Any]:
    payload = {
        "schema": "acfqp.standard_2048_fresh_terminal_source_binding.v42",
        "schema_version": SCHEMA_VERSION,
        "prepare_receipt_id": prepare_receipt["prepare_receipt_id"],
        "runner_attempt_id": runner_attempt["runner_attempt_id"],
        "worker_start_id": worker_start["worker_start_id"],
        "authority_consumption_id": authority_consumption[
            "authority_consumption_id"
        ],
        "source_commit": prepare_receipt["source_commit"],
        "source_tree": prepare_receipt["source_tree"],
        "source_manifest_id": prepare_receipt["source_manifest_id"],
        "fresh_terminal_preregistration_id": fresh_terminal_preregistration_id,
        "target_kernel_id": target_kernel_id,
        "adaptive_expression_overlay_id": adaptive_expression_overlay_id,
        "adaptive_expression_proof_id": adaptive_expression_proof_id,
        "adaptive_expression_model_id": adaptive_expression_model_id,
        "planner_id": planner_id,
        "binding_frozen_before_first_registered_target_transition": True,
    }
    return {
        **payload,
        "source_binding_id": domains.extension_content_id_v42(
            domains.CONSTRUCTION_K7_SOURCE_BINDING_V42_DOMAIN, payload
        ),
    }


def verify_campaign_source_binding_v42(
    raw_or_document: bytes | dict[str, Any],
    *,
    expected: dict[str, Any],
) -> dict[str, Any]:
    document = _canonical_document(raw_or_document, "V42 source binding")
    if set(document) != _SOURCE_BINDING_FIELDS:
        _fail("V42 source binding schema is not exact")
    if document != expected:
        _fail("V42 source binding differs from committed prepare and attempt authority")
    return document


def fixed_authority_root_v42(root: Path) -> Path:
    return root.resolve() / AUTHORITY_ROOT_RELATIVE


def fixed_evidence_root_v42(root: Path) -> Path:
    return root.resolve() / EVIDENCE_ROOT_RELATIVE


def classify_artifact_bytes_v42(path: Path, expected: bytes | None) -> str:
    try:
        observed = path.lstat()
    except FileNotFoundError:
        return "ABSENT"
    if not stat.S_ISREG(observed.st_mode):
        return "NONREGULAR"
    raw = path.read_bytes()
    if expected is None:
        return "PRESENT_UNCHECKED"
    if raw == expected:
        return "EXACT"
    if expected.startswith(raw):
        return "STRICT_PREFIX"
    return "DIVERGENT"


__all__ = (
    "ATTEMPT_NAME",
    "AUTHORITY_ROOT_RELATIVE",
    "AUTHORITY_CONSUMPTION_NAME",
    "CAMPAIGN_NAME",
    "EVIDENCE_ROOT_RELATIVE",
    "FAILURE_NAME",
    "FORMAL_IDENTITY",
    "FORMAL_SOURCE_ROOTS",
    "LAUNCH_ATTEMPT_JOURNAL_NAME",
    "LAUNCH_FAILURE_JOURNAL_NAME",
    "REQUIRED_FROZEN_SEMANTIC_SOURCE_FACTS",
    "PREPARE_ATTEMPT_JOURNAL_NAME",
    "PREPARE_FAILURE_JOURNAL_NAME",
    "PREPARE_RECEIPT_NAME",
    "TERMINAL_NAME",
    "VERIFICATION_NAME",
    "WORKER_START_NAME",
    "build_campaign_source_binding_v42",
    "build_authority_consumption_v42",
    "build_prepare_receipt_v42",
    "build_runner_attempt_v42",
    "build_source_manifest_from_commit_v42",
    "build_worker_start_v42",
    "classify_artifact_bytes_v42",
    "consume_supervisor_worker_authorization_v42",
    "fixed_authority_root_v42",
    "fixed_evidence_root_v42",
    "install_runtime_repository_import_guard_v42",
    "verify_campaign_source_binding_v42",
    "verify_consumed_formal_authority_v42",
    "verify_authority_consumption_v42",
    "verify_live_source_matches_manifest_v42",
    "verify_prepare_receipt_v42",
    "verify_runner_attempt_v42",
    "verify_source_manifest_document_v42",
    "verify_runtime_repository_modules_in_manifest_v42",
    "verify_worker_start_v42",
)
