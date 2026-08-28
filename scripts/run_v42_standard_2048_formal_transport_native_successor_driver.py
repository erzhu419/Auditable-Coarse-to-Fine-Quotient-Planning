#!/bin/sh
'''exec' /usr/bin/env -i LANG=C.UTF-8 LC_ALL=C.UTF-8 PATH=/usr/bin:/bin /usr/bin/python3 -I -S -B "$(/usr/bin/readlink -f "$0")" "$@"
' '''
from __future__ import annotations

"""Native V42r3 input verifier for the retained V42r2 activation successor.

This module performs read-only evidence verification only.  It rebuilds the
complete predecessor and successor DAG, then exposes the exact native IDs that
may authorize a V42r3 formal host probe.  It deliberately does not construct a
V42r1 production activation core and does not treat the compatibility anchor
as execution authority.  Historical unscoped SSH read-only/no-mutation fields
are checked only as retained document bytes; V42r3 re-labels them as legacy
claims and does not adopt them as end-to-end ingress facts.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import sys
from typing import Any, NoReturn


if __name__ == "__main__":
    raise RuntimeError(
        "native formal input verifier must be imported by the verified "
        "V42r3 launcher"
    )


ROOT = Path(__file__).resolve().parents[1]

from scripts import run_v42_standard_2048_formal_transport_driver as legacy  # noqa: E402
from scripts import run_v42_activation_successor_finalizer as successor_finalizer  # noqa: E402
from acfqp import (  # noqa: E402
    construction_k7_standard_2048_activation_successor_v42r2 as successor,
)


activation = legacy.activation
authority = legacy.authority
preformal = legacy.preformal
canonical_json_bytes = legacy.canonical_json_bytes
loads_canonical_json = legacy.loads_canonical_json


class V42NativeFormalInputError(RuntimeError):
    """A fail-closed native successor-evidence verification failure."""


def _fail(message: str) -> NoReturn:
    raise V42NativeFormalInputError(message)


MAX_EVIDENCE_BYTES = 64 * 1024**2

PREDECESSOR_FORMAL_PREFIX_EXPECTED_INVENTORY = (
    legacy.formal.LOCAL_KNOWN_HOSTS_NAME,
)

SUCCESSOR_SOURCE_MANIFEST_FILE = "ACTIVATION_SUCCESSOR_SOURCE_MANIFEST.json"
SUCCESSOR_PLAN_FILE = "ACTIVATION_SUCCESSOR_PLAN.json"
SUCCESSOR_LOCAL_ATTEMPT_FILE = "ACTIVATION_SUCCESSOR_LOCAL_ATTEMPT.json"
SUCCESSOR_NETWORK_START_FILE = (
    "ACTIVATION_SUCCESSOR_NETWORK_START.00000001.json"
)
SUCCESSOR_RECEIVER_OBSERVATION_FILE = (
    "ACTIVATION_SUCCESSOR_RECEIVER_OBSERVATION.00000001.json"
)
SUCCESSOR_PATH_RECEIPT_FILE = (
    "ACTIVATION_SUCCESSOR_PATH_PROVENANCE_RECEIPT.00000001.json"
)
SUCCESSOR_OBSERVATION_FILE = "ACTIVATION_SUCCESSOR_OBSERVATION.00000001.json"
SUCCESSOR_CLASSIFICATION_FILE = (
    "ACTIVATION_SUCCESSOR_CLASSIFICATION.00000001.json"
)
SUCCESSOR_SNAPSHOT_FILE = (
    "ACTIVATION_SUCCESSOR_READ_ONLY_SNAPSHOT.00000001.json"
)
OBSERVED_REMOTE_ATTEMPT_FILE = (
    "SUCCESSOR_OBSERVED_REMOTE_MATERIALIZATION_ATTEMPT.json"
)
OBSERVED_SOURCE_TERMINAL_FILE = (
    "SUCCESSOR_OBSERVED_SOURCE_MATERIALIZATION_TERMINAL.json"
)
SUCCESSOR_FINAL_FILE = "ACTIVATION_SUCCESSOR_FINAL_EVIDENCE_INDEX.json"
LEGACY_CORE_ANCHOR_FILE = "ACTIVATION_SUCCESSOR_LEGACY_CORE_ANCHOR.json"
SUCCESSOR_EVIDENCE_ROOTS_FILE = "ACTIVATION_SUCCESSOR_EVIDENCE_ROOTS.json"

SUCCESSOR_FILE_INVENTORY = (
    SUCCESSOR_SOURCE_MANIFEST_FILE,
    SUCCESSOR_PLAN_FILE,
    SUCCESSOR_LOCAL_ATTEMPT_FILE,
    SUCCESSOR_NETWORK_START_FILE,
    SUCCESSOR_RECEIVER_OBSERVATION_FILE,
    SUCCESSOR_PATH_RECEIPT_FILE,
    SUCCESSOR_OBSERVATION_FILE,
    SUCCESSOR_CLASSIFICATION_FILE,
    SUCCESSOR_SNAPSHOT_FILE,
    OBSERVED_REMOTE_ATTEMPT_FILE,
    OBSERVED_SOURCE_TERMINAL_FILE,
    SUCCESSOR_FINAL_FILE,
    LEGACY_CORE_ANCHOR_FILE,
    SUCCESSOR_EVIDENCE_ROOTS_FILE,
)
FORMAL_SUCCESSOR_EVIDENCE_ASSEMBLY_FILE = (
    "FORMAL_ACTIVATION_SUCCESSOR_EVIDENCE_ASSEMBLY.json"
)
SUCCESSOR_CONTROLLER_TCB_PATHS = frozenset(
    {
        "scripts/__init__.py",
        "scripts/launch_v42_activation_successor_or_formal.py",
        "scripts/launch_v42_preformal_upload_sender.py",
        "scripts/publish_v42_preformal_upload_journal.py",
        "scripts/run_v42_activation_successor_finalizer.py",
        "scripts/run_v42_materialization_activation.py",
        "scripts/run_v42_preformal_upload_sender.py",
        "scripts/run_v42_standard_2048_formal_transport_driver.py",
        "scripts/run_v42_standard_2048_formal_transport_successor_driver.py",
        "scripts/run_v42_standard_2048_remote_ordinal2.py",
        "scripts/v42_activation_successor_loader.py",
        "scripts/v42_activation_successor_receiver.py",
        "src/acfqp/__init__.py",
        "src/acfqp/artifacts.py",
        "src/acfqp/build_coverage.py",
        "src/acfqp/construction_k7_domain_registry_extension_v42.py",
        "src/acfqp/construction_k7_standard_2048_activation_successor_v42r2.py",
        "src/acfqp/construction_k7_standard_2048_formal_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_fresh_terminal_preregistration_v42.py",
        "src/acfqp/construction_k7_standard_2048_history_manifest_v42.py",
        "src/acfqp/construction_k7_standard_2048_materialization_activation_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_materialization_transport_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_process_supervision_v42r1.py",
        "src/acfqp/construction_k7_standard_2048_remote_execution_authority_v42r1.py",
        "src/acfqp/core.py",
        "src/acfqp/enumeration.py",
        "src/acfqp/phase3e_ids.py",
    }
)
_FROZEN_GIT_MODULE_NAME = "_acfqp_frozen_preformal_launcher_primitives"
_FROZEN_GIT_MODULE: object | None = None
_FROZEN_GIT_PRIMITIVES: Mapping[str, object] | None = None


def _hex(value: object, width: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != width
        or any(character not in "0123456789abcdef" for character in value)
    ):
        _fail(label + " changed type or hexadecimal width")
    return value


def _frozen_git_primitives() -> Mapping[str, object]:
    """Reuse the legacy one-load primitive module without re-executing it."""

    global _FROZEN_GIT_MODULE, _FROZEN_GIT_PRIMITIVES
    existing = sys.modules.get(_FROZEN_GIT_MODULE_NAME)
    if _FROZEN_GIT_PRIMITIVES is None:
        if existing is not None or _FROZEN_GIT_MODULE is not None:
            _fail("frozen Git primitive module existed before adapter-owned load")
        namespace = legacy._frozen_launcher_primitives()  # noqa: SLF001
        loaded = sys.modules.get(_FROZEN_GIT_MODULE_NAME)
        if loaded is None or vars(loaded) is not namespace:
            _fail("frozen Git primitive module identity changed during load")
        _FROZEN_GIT_MODULE = loaded
        _FROZEN_GIT_PRIMITIVES = namespace
    if (
        existing is not None
        and existing is not _FROZEN_GIT_MODULE
        or sys.modules.get(_FROZEN_GIT_MODULE_NAME) is not _FROZEN_GIT_MODULE
        or _FROZEN_GIT_PRIMITIVES is None
        or vars(_FROZEN_GIT_MODULE) is not _FROZEN_GIT_PRIMITIVES
    ):
        _fail("frozen Git primitive module changed after adapter-owned load")
    namespace = _FROZEN_GIT_PRIMITIVES
    required = {
        "_run_fixed_git_v42r1", "_open_absolute_directory_chain",
        "_read_relative_tcb_file_v42r1", "GIT_VERSION_STDOUT",
    }
    if not required <= namespace.keys():
        _fail("retained frozen Git primitive surface changed")
    return namespace


def _canonical_document(raw: bytes, label: str) -> dict[str, Any]:
    if type(raw) is not bytes or not raw or len(raw) > MAX_EVIDENCE_BYTES:
        _fail(label + " changed byte type, emptiness, or cap")
    try:
        document = loads_canonical_json(raw)
    except (TypeError, ValueError, UnicodeError) as error:
        raise V42NativeFormalInputError(
            label + " is not canonical JSON"
        ) from error
    if type(document) is not dict or canonical_json_bytes(document) != raw:
        _fail(label + " canonical bytes changed")
    return document


def _verify_identity_document(
    document: object, observed: os.stat_result, *, node_type: str,
    include_times: bool, label: str,
) -> None:
    expected_fields = {
        "node_type", "mode", "uid", "gid", "st_dev", "st_ino", "st_nlink",
        "st_size",
    }
    if include_times:
        expected_fields.update({"st_mtime_ns", "st_ctime_ns"})
    expected = {
        "node_type": node_type,
        "mode": stat.S_IMODE(observed.st_mode),
        "uid": observed.st_uid,
        "gid": observed.st_gid,
        "st_dev": observed.st_dev,
        "st_ino": observed.st_ino,
        "st_nlink": observed.st_nlink,
        "st_size": observed.st_size,
    }
    if include_times:
        expected.update(
            {"st_mtime_ns": observed.st_mtime_ns, "st_ctime_ns": observed.st_ctime_ns}
        )
    if type(document) is not dict or set(document) != expected_fields or document != expected:
        _fail(label + " identity changed")


def _read_root_documents(
    root: Path, names: Sequence[str], label: str
) -> tuple[
    dict[str, dict[str, Any]], dict[str, bytes], dict[str, Any], Any,
]:
    pin = legacy._EvidenceRootPin.open(root, label)  # noqa: SLF001
    try:
        inventory_before = pin.inventory()
        if inventory_before != sorted(names):
            _fail(label + " exact inventory changed")
        documents: dict[str, dict[str, Any]] = {}
        raws: dict[str, bytes] = {}
        for name in names:
            raw = pin.read(name, MAX_EVIDENCE_BYTES)
            raws[name] = raw
            documents[name] = _canonical_document(raw, name)
        if pin.inventory() != inventory_before:
            _fail(label + " inventory changed during read")
        pin.verify()
        identity = pin.identity()
    except BaseException:
        pin.close()
        raise
    return documents, raws, identity, pin


@dataclass(frozen=True)
class VerifiedSuccessorDocumentsV42r2:
    documents: Mapping[str, dict[str, Any]]
    raws: Mapping[str, bytes]
    ids: Mapping[str, str]
    final: dict[str, Any]
    legacy_core_anchor: dict[str, Any]


def _historical_successor_sources(
    source_manifest: Mapping[str, Any],
) -> tuple[dict[str, tuple[str, str, str]], dict[str, bytes]]:
    """Read the retained controller bytes from its declared historical tree."""

    commit = _hex(source_manifest.get("source_commit"), 40, "source commit")
    tree = _hex(source_manifest.get("source_tree"), 40, "source tree")
    fact_rows = source_manifest.get("source_facts")
    if type(fact_rows) is not list or any(type(row) is not dict for row in fact_rows):
        _fail("successor source fact rows changed type")
    facts = {row.get("relative_path"): row for row in fact_rows}
    if set(facts) != SUCCESSOR_CONTROLLER_TCB_PATHS or len(facts) != len(fact_rows):
        _fail("successor controller TCB source inventory changed")
    primitives = _frozen_git_primitives()
    run = primitives["_run_fixed_git_v42r1"]
    if not callable(run) or run("--version") != primitives["GIT_VERSION_STDOUT"]:
        _fail("frozen pinned Git version output changed")

    def selected_anchors() -> tuple[list[bytes], list[bytes]]:
        commit_rows = run(
            "-C", str(ROOT), "rev-parse", "--verify", commit + "^{commit}"
        ).splitlines()
        tree_rows = run(
            "-C", str(ROOT), "rev-parse", "--verify", commit + "^{tree}"
        ).splitlines()
        return commit_rows, tree_rows

    expected_anchors = ([commit.encode("ascii")], [tree.encode("ascii")])
    if selected_anchors() != expected_anchors:
        _fail("successor historical Git commit/tree anchor changed")
    listing = run(
        "-C", str(ROOT), "ls-tree", "-rz", "--full-tree", commit, "--",
        *sorted(SUCCESSOR_CONTROLLER_TCB_PATHS),
    )
    if selected_anchors() != expected_anchors:
        _fail("successor historical Git anchor changed across tree listing")
    records = listing.split(b"\0")
    if not records or records[-1] != b"":
        _fail("successor historical Git tree framing changed")
    git_tree: dict[str, tuple[str, str, str]] = {}
    for record in records[:-1]:
        try:
            header, relative_raw = record.split(b"\t", 1)
            mode_raw, kind_raw, oid_raw = header.split(b" ", 2)
            relative = relative_raw.decode("utf-8", errors="strict")
            row = (
                mode_raw.decode("ascii"),
                kind_raw.decode("ascii"),
                oid_raw.decode("ascii"),
            )
        except (ValueError, UnicodeError) as error:
            raise V42NativeFormalInputError(
                "successor historical Git tree row changed"
            ) from error
        if relative in git_tree or relative not in facts:
            _fail("successor historical Git tree inventory changed")
        git_tree[relative] = row
    if set(git_tree) != set(facts):
        _fail("successor historical Git tree omitted a controller source")
    raws: dict[str, bytes] = {}
    for relative in sorted(facts):
        fact = facts[relative]
        mode, kind, oid = git_tree[relative]
        if (
            mode != fact.get("git_mode")
            or kind != fact.get("git_object_type")
            or oid != fact.get("git_blob_oid")
            or kind != "blob"
        ):
            _fail("successor historical Git fact changed: " + relative)
        raw = run("-C", str(ROOT), "cat-file", "blob", oid)
        if (
            not raw
            or len(raw) > 4 * 1024**2
            or fact.get("byte_count") != len(raw)
            or fact.get("sha256") != hashlib.sha256(raw).hexdigest()
            or oid
            != hashlib.sha1(  # noqa: S324 - exact Git blob identity
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest()
        ):
            _fail("successor historical Git blob changed: " + relative)
        raws[relative] = raw
    if selected_anchors() != expected_anchors:
        _fail("successor historical Git anchor changed across blob reads")
    return git_tree, raws


def verify_successor_documents_v42r2(
    *, documents: Mapping[str, dict[str, Any]], raws: Mapping[str, bytes],
    expected_final_evidence_index_id: str,
    legacy_activation_plan: Mapping[str, Any],
    legacy_snapshot_tail: Mapping[str, Any],
    preactivation_resource_result_id: str,
    successor_evidence_root: Path,
    loader_source_raw: bytes,
    receiver_source_raw: bytes,
) -> VerifiedSuccessorDocumentsV42r2:
    """Verify the native chain, anchor, and exact nested-path receipt.

    This is intentionally exposed as a pure test surface.  All unknown fields
    remain covered by the owning content ID; every cross-document identity
    that authorizes the native V42r3 binding is required explicitly below.
    """

    if set(documents) != set(SUCCESSOR_FILE_INVENTORY):
        _fail("successor document inventory changed")
    if set(raws) != set(SUCCESSOR_FILE_INVENTORY):
        _fail("successor raw inventory changed")
    for name in SUCCESSOR_FILE_INVENTORY:
        if canonical_json_bytes(documents[name]) != raws[name]:
            _fail("successor document/raw bytes diverged: " + name)

    source_manifest = successor.verify_activation_successor_source_manifest_v42r2(
        documents[SUCCESSOR_SOURCE_MANIFEST_FILE]
    )
    git_tree, historical_raws = _historical_successor_sources(source_manifest)
    facts = {
        row["relative_path"]: row for row in source_manifest["source_facts"]
    }
    if set(facts) != SUCCESSOR_CONTROLLER_TCB_PATHS:
        _fail("successor controller TCB source inventory changed")
    for relative, fact in facts.items():
        raw = historical_raws[relative]
        if (
            git_tree.get(relative)
            != (
                fact.get("git_mode"), fact.get("git_object_type"),
                fact.get("git_blob_oid"),
            )
            or
            fact.get("byte_count") != len(raw)
            or fact.get("sha256") != hashlib.sha256(raw).hexdigest()
            or fact.get("git_blob_oid")
            != hashlib.sha1(  # noqa: S324 - exact Git blob identity
                b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
            ).hexdigest()
        ):
            _fail("successor controller TCB bytes changed: " + relative)
    if (
        loader_source_raw
        != historical_raws[successor.SUCCESSOR_LOADER_RELATIVE]
        or receiver_source_raw
        != historical_raws[successor.SUCCESSOR_RECEIVER_RELATIVE]
    ):
        _fail("successor loader or receiver differs from historical Git bytes")
    legacy_dispatch_fact = facts[
        successor_finalizer.LEGACY_ACTIVATION_DRIVER_RELATIVE
    ]
    legacy_dispatch_artifact = legacy_activation_plan.get(
        "activation_driver_artifact"
    )
    if (
        type(legacy_dispatch_artifact) is not dict
        or set(legacy_dispatch_artifact)
        != set(legacy_dispatch_fact)
        | {"file_mode", "committed_regular_file_required"}
        or any(
            legacy_dispatch_artifact.get(key) != value
            for key, value in legacy_dispatch_fact.items()
        )
        or legacy_dispatch_artifact.get("file_mode") != "0444"
        or legacy_dispatch_artifact.get("committed_regular_file_required") is not True
    ):
        _fail(
            "legacy dispatch driver differs between retained activation plan "
            "and successor source manifest"
        )
    plan = successor.verify_activation_successor_read_only_plan_v42r2(
        documents[SUCCESSOR_PLAN_FILE],
        legacy_activation_plan=legacy_activation_plan,
        legacy_snapshot_tail=legacy_snapshot_tail,
        successor_source_manifest=source_manifest,
        successor_evidence_root=str(successor_evidence_root),
        loader_source_raw=loader_source_raw,
        receiver_source_raw=receiver_source_raw,
    )
    local_attempt = successor_finalizer.verify_local_attempt_v42r2(
        documents[SUCCESSOR_LOCAL_ATTEMPT_FILE], successor_plan=plan,
        controller_source_manifest=source_manifest,
    )
    successor_finalizer.verify_network_start_v42r2(
        documents[SUCCESSOR_NETWORK_START_FILE], successor_plan=plan,
        local_attempt=local_attempt,
    )
    receiver_observation = (
        successor.verify_activation_successor_receiver_observation_v42r2(
            documents[SUCCESSOR_RECEIVER_OBSERVATION_FILE]
        )
    )
    path_receipt = successor.verify_activation_successor_path_provenance_receipt_v42r2(
        documents[SUCCESSOR_PATH_RECEIPT_FILE], plan=plan,
        receiver_observation=receiver_observation,
    )
    normalized_observation = successor.build_activation_successor_observation_v42r2(
        plan=plan, path_provenance_receipt=path_receipt
    )
    if documents[SUCCESSOR_OBSERVATION_FILE] != normalized_observation:
        _fail("retained normalized successor observation changed")
    normalized_observation = successor.verify_activation_successor_observation_v42r2(
        normalized_observation, plan=plan
    )
    classification = successor.verify_activation_successor_classification_v42r2(
        documents[SUCCESSOR_CLASSIFICATION_FILE], plan=plan,
        observation=normalized_observation,
    )
    snapshot = successor.verify_activation_successor_snapshot_v42r2(
        documents[SUCCESSOR_SNAPSHOT_FILE], plan=plan,
        observation=normalized_observation, classification=classification,
    )
    final = successor.verify_activation_successor_final_evidence_index_v42r2(
        documents[SUCCESSOR_FINAL_FILE], plan=plan, snapshot=snapshot,
        classification=classification,
    )
    expected_final = _hex(
        expected_final_evidence_index_id, 64,
        "expected successor final evidence index ID",
    )
    if final["activation_successor_final_evidence_index_id"] != expected_final:
        _fail("native successor final differs from expected identity")
    anchor = successor.verify_activation_successor_legacy_core_anchor_v42r2(
        documents[LEGACY_CORE_ANCHOR_FILE], final_evidence_index=final,
        preactivation_resource_result_id=preactivation_resource_result_id,
    )
    embedded = normalized_observation["documents"]
    if (
        raws[OBSERVED_REMOTE_ATTEMPT_FILE]
        != canonical_json_bytes(
            embedded[successor.REMOTE_ATTEMPT_RELATIVE_PATH]
        )
        or raws[OBSERVED_SOURCE_TERMINAL_FILE]
        != canonical_json_bytes(
            embedded[successor.SOURCE_TERMINAL_RELATIVE_PATH]
        )
    ):
        _fail("separately retained observed documents lost path-receipt bytes")
    ids = {
        SUCCESSOR_SOURCE_MANIFEST_FILE: source_manifest[
            "activation_successor_source_manifest_id"
        ],
        SUCCESSOR_PLAN_FILE: plan["activation_successor_read_only_plan_id"],
        SUCCESSOR_LOCAL_ATTEMPT_FILE: local_attempt[
            "activation_successor_local_read_only_attempt_id"
        ],
        SUCCESSOR_NETWORK_START_FILE: documents[SUCCESSOR_NETWORK_START_FILE][
            "activation_successor_read_only_network_start_id"
        ],
        SUCCESSOR_RECEIVER_OBSERVATION_FILE: receiver_observation[
            "activation_successor_read_only_observation_id"
        ],
        SUCCESSOR_PATH_RECEIPT_FILE: path_receipt[
            "activation_successor_path_provenance_receipt_id"
        ],
        SUCCESSOR_OBSERVATION_FILE: normalized_observation[
            "activation_successor_observation_id"
        ],
        SUCCESSOR_CLASSIFICATION_FILE: classification[
            "activation_successor_classification_id"
        ],
        SUCCESSOR_SNAPSHOT_FILE: snapshot[
            "activation_successor_read_only_snapshot_id"
        ],
        SUCCESSOR_FINAL_FILE: final[
            "activation_successor_final_evidence_index_id"
        ],
        LEGACY_CORE_ANCHOR_FILE: anchor[
            "activation_successor_legacy_core_anchor_id"
        ],
    }
    return VerifiedSuccessorDocumentsV42r2(
        documents=dict(documents), raws=dict(raws), ids=ids,
        final=final, legacy_core_anchor=anchor,
    )


@dataclass(frozen=True)
class VerifiedNativeFormalInputsV42r3:
    successor: VerifiedSuccessorDocumentsV42r2
    activation_terminal_raw: bytes
    source_manifest_raw: bytes
    transport_manifest_raw: bytes
    native_activation_inputs: Mapping[str, Any]
    predecessor_activation_evidence_root: Path
    successor_evidence_root: Path
    evidence_root_identities: Mapping[str, Mapping[str, Any]]
    predecessor_formal_prefix: Mapping[str, Any]


def verify_failed_v42r1_formal_prefix_read_only() -> dict[str, Any]:
    """Verify and describe the retained pre-effect V42r1 formal prefix."""

    root = legacy.formal.LOCAL_FORMAL_JOURNAL_ROOT
    pin = legacy._EvidenceRootPin.open(  # noqa: SLF001
        root, "failed V42r1 formal journal prefix"
    )
    try:
        inventory = pin.inventory()
        if inventory != list(PREDECESSOR_FORMAL_PREFIX_EXPECTED_INVENTORY):
            _fail("failed V42r1 formal prefix inventory changed")
        known_hosts_raw = pin.read(legacy.formal.LOCAL_KNOWN_HOSTS_NAME, 4096)
        if known_hosts_raw != preformal.PINNED_KNOWN_HOSTS_BYTES:
            _fail("failed V42r1 formal prefix known-host bytes changed")
        observed = os.fstat(pin.descriptor)
        root_identity = legacy._journal_root_identity(observed)  # noqa: SLF001
        anchor_path = root.parent / legacy._journal_anchor_name(  # noqa: SLF001
            "ROOT_IDENTITY.json"
        )
        anchor_raw = legacy._stable_read(anchor_path, 4096, mode=0o400)  # noqa: SLF001
        anchor = _canonical_document(anchor_raw, "failed V42r1 root anchor")
        if anchor != root_identity:
            _fail("failed V42r1 formal root anchor changed")
        pin.verify()
        return {
            "predecessor_formal_journal_root": str(root),
            "predecessor_formal_root_identity": pin.identity(),
            "predecessor_formal_root_anchor_sha256": hashlib.sha256(
                anchor_raw
            ).hexdigest(),
            "predecessor_formal_exact_inventory": inventory,
            "predecessor_formal_known_hosts_sha256": hashlib.sha256(
                known_hosts_raw
            ).hexdigest(),
            "predecessor_formal_plan_present": False,
            "predecessor_formal_attempt_present": False,
            "predecessor_formal_network_marker_present": False,
            "predecessor_formal_effect_may_have_started": False,
            "predecessor_formal_prefix_opened_read_only": True,
            "predecessor_formal_prefix_mutated": False,
        }
    finally:
        pin.close()


def build_native_activation_inputs_v42r3(
    *, verified_successor: VerifiedSuccessorDocumentsV42r2,
    materialization_activation_plan: Mapping[str, Any],
    predecessor_snapshot_tail_id: str,
    predecessor_classification: Mapping[str, Any],
    predecessor_activation_terminal: Mapping[str, Any],
    preactivation_resource_result: Mapping[str, Any],
    source_manifest: Mapping[str, Any],
    transport_manifest: Mapping[str, Any],
    local_materialization_attempt: Mapping[str, Any],
    remote_materialization_attempt: Mapping[str, Any],
    materialization_terminal: Mapping[str, Any],
) -> dict[str, Any]:
    """Project verified documents onto the native V42r3 authority surface."""

    successor_plan = verified_successor.documents[SUCCESSOR_PLAN_FILE]
    path_receipt = verified_successor.documents[SUCCESSOR_PATH_RECEIPT_FILE]
    final = verified_successor.final
    return {
        "formal_identity": final["formal_identity"],
        "global_execution_ordinal": final["global_execution_ordinal"],
        "activation_successor_source_manifest_id": verified_successor.ids[
            SUCCESSOR_SOURCE_MANIFEST_FILE
        ],
        "activation_successor_read_only_plan_id": verified_successor.ids[
            SUCCESSOR_PLAN_FILE
        ],
        "activation_successor_path_provenance_receipt_id": (
            verified_successor.ids[SUCCESSOR_PATH_RECEIPT_FILE]
        ),
        "activation_successor_classification_id": verified_successor.ids[
            SUCCESSOR_CLASSIFICATION_FILE
        ],
        "activation_successor_read_only_snapshot_id": verified_successor.ids[
            SUCCESSOR_SNAPSHOT_FILE
        ],
        "activation_successor_final_evidence_index_id": verified_successor.ids[
            SUCCESSOR_FINAL_FILE
        ],
        "predecessor_materialization_activation_plan_id": (
            materialization_activation_plan["materialization_activation_plan_id"]
        ),
        "predecessor_activation_read_only_snapshot_tail_id": (
            predecessor_snapshot_tail_id
        ),
        "predecessor_activation_classification_id": predecessor_classification[
            "materialization_activation_classification_id"
        ],
        "predecessor_remote_materialization_transport_terminal_id": (
            predecessor_activation_terminal[
                "remote_materialization_transport_terminal_id"
            ]
        ),
        "preactivation_resource_result_id": preactivation_resource_result[
            "preactivation_resource_result_id"
        ],
        "preactivation_observed_python": dict(
            preactivation_resource_result["observed_python"]
        ),
        "preactivation_cgroup_memory_ancestry": [
            dict(row)
            for row in preactivation_resource_result["cgroup_memory_ancestry"]
        ],
        "preactivation_memory_total_bytes": preactivation_resource_result[
            "memory_total_bytes"
        ],
        "preactivation_memory_available_bytes": preactivation_resource_result[
            "memory_available_bytes"
        ],
        "preactivation_all_resource_gates_passed": preactivation_resource_result[
            "all_resource_gates_passed"
        ],
        "preactivation_read_only_observation_completed": (
            preactivation_resource_result["read_only_observation_completed"]
        ),
        "preactivation_remote_mutation_performed": preactivation_resource_result[
            "remote_mutation_performed"
        ],
        "source_commit": source_manifest["source_commit"],
        "source_tree": source_manifest["source_tree"],
        "source_manifest_id": source_manifest["source_manifest_id"],
        "transport_manifest_id": transport_manifest["transport_manifest_id"],
        "local_materialization_attempt_id": local_materialization_attempt[
            "local_materialization_attempt_id"
        ],
        "remote_materialization_attempt_id": remote_materialization_attempt[
            "remote_materialization_attempt_id"
        ],
        "materialization_terminal_id": materialization_terminal[
            "materialization_terminal_id"
        ],
        "fixed_remote_root": successor_plan["fixed_remote_root"],
        "remote_source_root": successor_plan["remote_source_root"],
        "remote_target_alias": successor_plan["remote_target_alias"],
        "expected_remote_hostname": successor_plan["expected_remote_hostname"],
        "observed_remote_hostname": path_receipt["observed_hostname"],
        "observed_remote_user": path_receipt["observed_user"],
        "observed_remote_uid": path_receipt["observed_uid"],
        "observed_remote_gid": path_receipt["observed_gid"],
        "non_authoritative_compatibility_artifact_id": verified_successor.ids[
            LEGACY_CORE_ANCHOR_FILE
        ],
        "legacy_activation_final_evidence_index_claimed": False,
        "legacy_snapshot_or_final_synthesized": False,
        "activation_effect_replay_authorized": False,
        "native_nested_path_evidence_complete": True,
    }


def _verify_predecessor_and_build_native_inputs(
    *, predecessor_root: Path,
    successor_root: Path,
    successor_documents: Mapping[str, dict[str, Any]],
    successor_raws: Mapping[str, bytes],
    expected_final_evidence_index_id: str,
) -> tuple[
    VerifiedSuccessorDocumentsV42r2, bytes, bytes, bytes,
    dict[str, Any], dict[str, Any],
]:
    """Rebuild the real predecessor DAG without a legacy collector final."""

    pin = legacy._EvidenceRootPin.open(  # noqa: SLF001
        predecessor_root, "predecessor activation evidence root"
    )
    other_pins: list[Any] = []
    try:
        if legacy.ACTIVATION_FINAL_EVIDENCE_INDEX_FILE in pin.inventory():
            _fail("predecessor activation evidence unexpectedly contains a legacy final")
        roots_raw = pin.read(legacy.ACTIVATION_EVIDENCE_ROOTS_FILE, 4 * 1024**2)
        roots = _canonical_document(roots_raw, legacy.ACTIVATION_EVIDENCE_ROOTS_FILE)
        expected_root_fields = {
            "schema", "activation_evidence_root", "control_evidence_root",
            "preformal_evidence_root", "resource_evidence_root",
            "controls_are_retained_by_stable_reference_not_hardlink_or_copy",
            "expected_exact_control_names", "control_reference_snapshot",
            "formal_loader_must_reverify_all_control_bytes_and_storage",
            "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim",
        }
        if (
            set(roots) != expected_root_fields
            or
            roots.get("schema")
            != "acfqp.v42_materialization_activation_evidence_roots.v42r1"
            or roots.get("activation_evidence_root") != str(predecessor_root)
            or roots.get(
                "controls_are_retained_by_stable_reference_not_hardlink_or_copy"
            ) is not True
            or roots.get(
                "formal_loader_must_reverify_all_control_bytes_and_storage"
            ) is not True
            or roots.get("expected_exact_control_names")
            != list(preformal.CONTROL_NAMES)
            or roots.get(
                "same_uid_coordinated_replacement_of_named_root_and_all_persistent_anchors_excluded_from_claim"
            ) is not True
        ):
            _fail("predecessor activation evidence roots index changed")

        def indexed_pin(field: str, label: str) -> Any:
            value = roots.get(field)
            if type(value) is not str:
                _fail("predecessor evidence roots index changed: " + field)
            path = Path(value)
            selected = legacy._EvidenceRootPin.open(path, label)  # noqa: SLF001
            other_pins.append(selected)
            return selected

        preformal_pin = indexed_pin("preformal_evidence_root", "preformal evidence root")
        resource_pin = indexed_pin("resource_evidence_root", "resource evidence root")
        control_pin = indexed_pin("control_evidence_root", "control evidence root")

        controls = {
            name: control_pin.read(name, 2 * 1024**3)
            for name in preformal.CONTROL_NAMES
        }
        if control_pin.inventory() != list(preformal.CONTROL_NAMES):
            _fail("predecessor control inventory changed")
        control_snapshot = roots.get("control_reference_snapshot")
        if (
            type(control_snapshot) is not dict
            or control_snapshot.get("control_root")
            != str(Path(str(roots["control_evidence_root"])))
            or control_snapshot.get("exact_inventory")
            != list(preformal.CONTROL_NAMES)
            or control_snapshot.get("all_files_read_nofollow_from_pinned_root")
            is not True
            or control_snapshot.get("all_file_bytes_hashed_with_bounded_reads")
            is not True
            or control_snapshot.get("whole_root_first_last_snapshot_equal")
            is not True
            or type(control_snapshot.get("control_facts")) is not list
        ):
            _fail("predecessor activation control reference snapshot changed")
        snapshot_facts = {
            row.get("name"): row for row in control_snapshot["control_facts"]
            if type(row) is dict
        }
        if set(snapshot_facts) != set(preformal.CONTROL_NAMES):
            _fail("predecessor activation control fact inventory changed")
        for name, raw in controls.items():
            row = snapshot_facts[name]
            if (
                row.get("path") != str(Path(str(roots["control_evidence_root"])) / name)
                or row.get("mode") != 0o400
                or row.get("uid") != os.geteuid()
                or row.get("gid") != os.getegid()
                or row.get("st_nlink") != 1
                or row.get("byte_count") != len(raw)
                or row.get("sha256") != hashlib.sha256(raw).hexdigest()
            ):
                _fail("predecessor activation control fact changed: " + name)
        predecessor_chain: list[Any] = []
        if legacy.PREDECESSOR_CHAIN_FILE in preformal_pin.inventory():
            chain_raw = preformal_pin.read(
                legacy.PREDECESSOR_CHAIN_FILE, MAX_EVIDENCE_BYTES
            )
            chain_value = loads_canonical_json(chain_raw)
            if type(chain_value) is not list or canonical_json_bytes(chain_value) != chain_raw:
                _fail("preformal predecessor chain changed")
            predecessor_chain = chain_value

        def read_doc(selected: Any, name: str) -> tuple[dict[str, Any], bytes]:
            raw = selected.read(name, MAX_EVIDENCE_BYTES)
            return _canonical_document(raw, name), raw

        p_plan, _ = read_doc(preformal_pin, legacy.PREFORMAL_PLAN_FILE)
        p_attempt, _ = read_doc(preformal_pin, legacy.PREFORMAL_ATTEMPT_FILE)
        p_receipt, _ = read_doc(pin, legacy.PREFORMAL_RECEIPT_FILE)
        p_outcome, _ = read_doc(preformal_pin, legacy.PREFORMAL_OUTCOME_FILE)
        resource_plan_doc, _ = read_doc(resource_pin, legacy.PREACTIVATION_PLAN_FILE)
        resource_result_doc, _ = read_doc(resource_pin, legacy.PREACTIVATION_RESULT_FILE)
        activation_plan_doc, _ = read_doc(pin, legacy.ACTIVATION_PLAN_FILE)
        local_activation_doc, _ = read_doc(pin, legacy.ACTIVATION_ATTEMPT_FILE)
        network_start_doc, _ = read_doc(pin, legacy.ACTIVATION_NETWORK_START_FILE)
        remote_activation_doc, _ = read_doc(pin, legacy.REMOTE_ACTIVATION_ATTEMPT_FILE)
        service_doc, _ = read_doc(pin, legacy.ACTIVATION_SERVICE_RECEIPT_FILE)
        ready_doc, _ = read_doc(pin, legacy.ACTIVATION_READY_FILE)
        activation_terminal_doc, activation_terminal_raw = read_doc(
            pin, legacy.ACTIVATION_TERMINAL_FILE
        )
        source_doc, source_raw = read_doc(pin, authority.SOURCE_MANIFEST_NAME)
        transport_doc, transport_raw = read_doc(pin, authority.TRANSPORT_MANIFEST_NAME)
        local_materialization_doc, local_materialization_raw = read_doc(
            pin, authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME
        )

        successor_source_manifest = (
            successor.verify_activation_successor_source_manifest_v42r2(
                successor_documents[SUCCESSOR_SOURCE_MANIFEST_FILE]
            )
        )
        _successor_git_tree, successor_programs = _historical_successor_sources(
            successor_source_manifest
        )
        programs = {
            relative: successor_programs[relative]
            for relative in (
                preformal.PREFORMAL_LOADER_SOURCE_RELATIVE,
                preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE,
                legacy.ACTIVATION_LOADER_RELATIVE,
                legacy.ACTIVATION_RECEIVER_RELATIVE,
                legacy.ACTIVATION_SERVICE_RELATIVE,
                legacy.ACTIVATION_DRIVER_RELATIVE,
                legacy.ACTIVATION_AUTHORITY_RELATIVE,
            )
        }
        verified_plan = preformal.verify_preformal_upload_plan_against_controls_v42r1(
            p_plan, control_raw_by_name=controls,
            loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
            receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
            predecessor_chain=predecessor_chain,
        )
        verified_attempt = preformal.verify_preformal_upload_attempt_against_controls_v42r1(
            p_attempt, plan=verified_plan, control_raw_by_name=controls,
            loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
            receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
            predecessor_chain=predecessor_chain,
        )
        verified_receipt = preformal.verify_preformal_upload_receipt_against_controls_v42r1(
            p_receipt, plan=verified_plan, attempt=verified_attempt,
            control_raw_by_name=controls,
            loader_source_raw=programs[preformal.PREFORMAL_LOADER_SOURCE_RELATIVE],
            receiver_source_raw=programs[preformal.PREFORMAL_RECEIVER_SOURCE_RELATIVE],
            predecessor_chain=predecessor_chain,
        )
        verified_outcome = preformal.verify_preformal_upload_outcome_v42r1(
            p_outcome, plan=verified_plan, attempt=verified_attempt,
            receipt=verified_receipt,
        )
        verified_resource_plan = activation.verify_preactivation_resource_probe_plan_v42r1(
            resource_plan_doc, preformal_plan=verified_plan,
            preformal_attempt=verified_attempt, preformal_receipt=verified_receipt,
            preformal_outcome=verified_outcome,
            loader_source_raw=programs[legacy.ACTIVATION_LOADER_RELATIVE],
            receiver_source_raw=programs[legacy.ACTIVATION_RECEIVER_RELATIVE],
            service_source_raw=programs[legacy.ACTIVATION_SERVICE_RELATIVE],
            driver_source_raw=programs[legacy.ACTIVATION_DRIVER_RELATIVE],
            activation_authority_source_raw=programs[legacy.ACTIVATION_AUTHORITY_RELATIVE],
            control_raw_by_name=controls,
        )
        verified_resource_result = activation.verify_preactivation_resource_result_v42r1(
            resource_result_doc, resource_plan=verified_resource_plan,
            preformal_receipt=verified_receipt,
        )
        verified_activation_plan = activation.verify_materialization_activation_plan_v42r1(
            activation_plan_doc, preformal_plan=verified_plan,
            preformal_attempt=verified_attempt,
            resource_plan=verified_resource_plan,
            resource_result=verified_resource_result,
            preformal_receipt=verified_receipt, preformal_outcome=verified_outcome,
            control_raw_by_name=controls,
            loader_source_raw=programs[legacy.ACTIVATION_LOADER_RELATIVE],
            receiver_source_raw=programs[legacy.ACTIVATION_RECEIVER_RELATIVE],
            service_source_raw=programs[legacy.ACTIVATION_SERVICE_RELATIVE],
            driver_source_raw=programs[legacy.ACTIVATION_DRIVER_RELATIVE],
            activation_authority_source_raw=programs[legacy.ACTIVATION_AUTHORITY_RELATIVE],
        )
        verified_local_activation = activation.verify_local_materialization_activation_attempt_v42r1(
            local_activation_doc, activation_plan=verified_activation_plan
        )
        verified_network = activation.verify_materialization_activation_network_start_v42r1(
            network_start_doc, activation_plan=verified_activation_plan,
            local_attempt=verified_local_activation,
        )
        verified_remote_activation = activation.verify_remote_materialization_activation_attempt_v42r1(
            remote_activation_doc, activation_plan=verified_activation_plan,
            local_attempt=verified_local_activation, network_start=verified_network,
        )
        verified_service = activation.verify_remote_activation_service_receipt_v42r1(
            service_doc, activation_plan=verified_activation_plan,
            remote_attempt=verified_remote_activation,
        )
        verified_ready = activation.verify_remote_activation_publish_ready_v42r1(
            ready_doc, activation_plan=verified_activation_plan,
            remote_attempt=verified_remote_activation,
            service_receipt=verified_service, preformal_receipt=verified_receipt,
        )
        verified_activation_terminal = activation.verify_remote_materialization_transport_terminal_v42r1(
            activation_terminal_raw, activation_plan=verified_activation_plan,
            remote_attempt=verified_remote_activation,
            service_receipt=verified_service, publish_ready=verified_ready,
            preformal_receipt=verified_receipt,
        )
        verified_source = authority.verify_source_manifest_v42r1(source_raw)
        verified_transport = authority.verify_transport_manifest_v42r1(
            transport_raw, source_manifest=verified_source
        )
        verified_local_materialization = authority.verify_local_materialization_attempt_v42r1(
            local_materialization_raw, source_manifest=verified_source,
            transport_manifest=verified_transport,
        )
        predecessor_remote_raw = pin.read(
            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME, MAX_EVIDENCE_BYTES
        )
        predecessor_remote_document = _canonical_document(
            predecessor_remote_raw, authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME
        )
        snapshot_names = sorted(
            name for name in pin.inventory()
            if name.startswith(legacy.ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX)
            and name.endswith(".json")
        )
        if not snapshot_names or len(snapshot_names) > 4096:
            _fail("predecessor activation snapshot inventory changed")
        previous: str | None = None
        tail: dict[str, Any] | None = None
        tail_rebuilt_classification: dict[str, Any] | None = None
        complete_remote_documents = {
            "remote_attempt": remote_activation_doc,
            "service_receipt": service_doc,
            "publish_ready": ready_doc,
            "terminal": activation_terminal_doc,
            "failure": None,
        }
        known_fixed_documents = {
            authority.SOURCE_MANIFEST_NAME: source_doc,
            authority.TRANSPORT_MANIFEST_NAME: transport_doc,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: local_materialization_doc,
            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME: predecessor_remote_document,
        }
        snapshot_fields = {
            "schema", "materialization_activation_plan_id", "snapshot_ordinal",
            "previous_snapshot_id", "observation", "classification",
            "remote_observation_only", "activation_effect_replay_authorized",
            "activation_read_only_snapshot_id",
        }
        for ordinal, name in enumerate(snapshot_names, start=1):
            if name != legacy.ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX + f"{ordinal:08d}.json":
                _fail("predecessor activation snapshot ordinals changed")
            snapshot_raw = pin.read(name, MAX_EVIDENCE_BYTES)
            snapshot = _canonical_document(snapshot_raw, name)
            payload = dict(snapshot)
            snapshot_id = _hex(
                payload.pop("activation_read_only_snapshot_id", None), 64,
                "predecessor activation read-only snapshot ID",
            )
            if snapshot_id != hashlib.sha256(
                b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
                + canonical_json_bytes(payload)
            ).hexdigest():
                _fail("predecessor activation read-only snapshot ID changed")
            observation = snapshot.get("observation")
            classification = snapshot.get("classification")
            if (
                set(snapshot) != snapshot_fields
                or snapshot.get("schema")
                != "acfqp.v42_materialization_activation_read_only_snapshot.v42r1"
                or snapshot.get("materialization_activation_plan_id")
                != verified_activation_plan["materialization_activation_plan_id"]
                or snapshot.get("snapshot_ordinal") != ordinal
                or snapshot.get("previous_snapshot_id") != previous
                or snapshot.get("remote_observation_only") is not True
                or snapshot.get("activation_effect_replay_authorized") is not False
                or type(observation) is not dict
                or type(classification) is not dict
            ):
                _fail("predecessor activation snapshot chain changed")
            remote_documents = observation.get("remote_documents")
            fixed_evidence = observation.get("fixed_root_evidence")
            fixed_documents = (
                None if type(fixed_evidence) is not dict
                else fixed_evidence.get("documents")
            )
            fixed_evidence_valid = fixed_evidence is None or (
                type(fixed_evidence) is dict
                and fixed_evidence.get("inventory_before")
                == fixed_evidence.get("inventory_after")
                and fixed_evidence.get("collected_subset_only_not_whole_tree")
                is True
                and type(fixed_documents) is dict
                and {
                    authority.SOURCE_MANIFEST_NAME,
                    authority.TRANSPORT_MANIFEST_NAME,
                    authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
                } <= set(fixed_documents)
                and set(fixed_documents) <= set(known_fixed_documents)
                and all(
                    fixed_documents[key] == known_fixed_documents[key]
                    for key in fixed_documents
                )
            )
            if (
                observation.get("materialization_activation_plan_id")
                != verified_activation_plan["materialization_activation_plan_id"]
                or observation.get("local_materialization_activation_attempt_id")
                != verified_local_activation[
                    "local_materialization_activation_attempt_id"
                ]
                or observation.get("observation_before")
                != observation.get("observation_after")
                or type(remote_documents) is not dict
                or set(remote_documents) != set(complete_remote_documents)
                or any(
                    remote_documents[key] is not None
                    and remote_documents[key] != complete_remote_documents[key]
                    for key in remote_documents
                )
                or observation.get("remote_mutation_performed") is not False
                or observation.get(
                    "only_read_only_ssh_ingress_and_systemctl_query_processes_started"
                ) is not True
                or observation.get(
                    "additional_durable_or_mutating_remote_process_started"
                ) is not False
                or observation.get("activation_retry_authorized") is not False
                or not fixed_evidence_valid
            ):
                _fail("predecessor activation snapshot observation changed")
            rebuilt = activation.verify_materialization_activation_classification_v42r1(
                classification, activation_plan=verified_activation_plan,
                local_attempt=verified_local_activation,
                network_start=verified_network, preformal_receipt=verified_receipt,
                remote_attempt=remote_documents["remote_attempt"],
                service_receipt=remote_documents["service_receipt"],
                publish_ready=remote_documents["publish_ready"],
                terminal=remote_documents["terminal"],
                failure=remote_documents["failure"],
                observation_before=observation.get("observation_before"),
                observation_after=observation.get("observation_after"),
            )
            previous = snapshot_id
            tail = snapshot
            tail_rebuilt_classification = rebuilt
        assert tail is not None and previous is not None
        tail_classification = tail.get("classification")
        tail_observation = tail.get("observation")
        if type(tail_classification) is not dict or type(tail_observation) is not dict:
            _fail("predecessor activation snapshot tail changed type")
        assert tail_rebuilt_classification is not None
        rebuilt_classification = tail_rebuilt_classification
        if rebuilt_classification.get("classification") != activation.CLASSIFICATION_SUCCESS:
            _fail("predecessor activation snapshot tail is not successful")
        fixed = tail_observation.get("fixed_root_evidence")
        expected_fixed_documents = {
            authority.SOURCE_MANIFEST_NAME: source_doc,
            authority.TRANSPORT_MANIFEST_NAME: transport_doc,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME: local_materialization_doc,
            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME: predecessor_remote_document,
        }
        if (
            tail.get("materialization_activation_plan_id")
            != verified_activation_plan["materialization_activation_plan_id"]
            or tail.get("remote_observation_only") is not True
            or tail.get("activation_effect_replay_authorized") is not False
            or tail_observation.get("observation_before")
            != tail_observation.get("observation_after")
            or tail_observation.get("remote_mutation_performed") is not False
            or tail_observation.get(
                "only_read_only_ssh_ingress_and_systemctl_query_processes_started"
            ) is not True
            or tail_observation.get(
                "additional_durable_or_mutating_remote_process_started"
            ) is not False
            or tail_observation.get("activation_retry_authorized") is not False
            or tail_observation.get("remote_documents")
            != complete_remote_documents
            or type(fixed) is not dict
            or fixed.get("inventory_before") != fixed.get("inventory_after")
            or fixed.get("documents") != expected_fixed_documents
            or fixed.get("collected_subset_only_not_whole_tree") is not True
            or type(fixed.get("inventory_before")) is not list
            or "source" not in fixed.get("inventory_before", [])
            or authority.MATERIALIZATION_TERMINAL_NAME
            in fixed.get("inventory_before", [])
        ):
            _fail("predecessor successful tail changed its legacy claim set")

        loader_source_raw = successor_programs[successor.SUCCESSOR_LOADER_RELATIVE]
        receiver_source_raw = successor_programs[
            successor.SUCCESSOR_RECEIVER_RELATIVE
        ]
        verified_successor = verify_successor_documents_v42r2(
            documents=successor_documents, raws=successor_raws,
            expected_final_evidence_index_id=expected_final_evidence_index_id,
            legacy_activation_plan=verified_activation_plan,
            legacy_snapshot_tail=tail,
            preactivation_resource_result_id=verified_resource_result[
                "preactivation_resource_result_id"
            ],
            successor_evidence_root=successor_root,
            loader_source_raw=loader_source_raw,
            receiver_source_raw=receiver_source_raw,
        )
        embedded = verified_successor.documents[SUCCESSOR_OBSERVATION_FILE][
            "documents"
        ]
        for relative, predecessor_raw in (
            (authority.SOURCE_MANIFEST_NAME, source_raw),
            (authority.TRANSPORT_MANIFEST_NAME, transport_raw),
            (authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME, local_materialization_raw),
        ):
            if canonical_json_bytes(embedded[relative]) != predecessor_raw:
                _fail("successor path receipt differs from predecessor: " + relative)
        observed_remote_raw = verified_successor.raws[OBSERVED_REMOTE_ATTEMPT_FILE]
        if observed_remote_raw != predecessor_remote_raw:
            _fail("successor remote attempt bytes differ from predecessor evidence")
        verified_remote_materialization = authority.verify_remote_materialization_attempt_v42r1(
            observed_remote_raw,
            local_materialization_attempt=verified_local_materialization,
            source_manifest=verified_source, transport_manifest=verified_transport,
        )
        verified_bootstrap_terminal = authority.verify_materialization_terminal_v42r1(
            verified_successor.raws[OBSERVED_SOURCE_TERMINAL_FILE],
            local_materialization_attempt=verified_local_materialization,
            remote_materialization_attempt=verified_remote_materialization,
            source_manifest=verified_source, transport_manifest=verified_transport,
        )
        final = verified_successor.final
        predecessor_links = {
            "legacy_materialization_activation_plan_id": verified_activation_plan[
                "materialization_activation_plan_id"
            ],
            "legacy_activation_read_only_snapshot_tail_id": previous,
            "legacy_activation_classification_id": rebuilt_classification[
                "materialization_activation_classification_id"
            ],
            "legacy_remote_materialization_transport_terminal_id": verified_activation_terminal[
                "remote_materialization_transport_terminal_id"
            ],
            "source_manifest_id": verified_source["source_manifest_id"],
            "transport_manifest_id": verified_transport["transport_manifest_id"],
            "local_materialization_attempt_id": verified_local_materialization[
                "local_materialization_attempt_id"
            ],
            "remote_materialization_attempt_id": verified_remote_materialization[
                "remote_materialization_attempt_id"
            ],
            "materialization_terminal_id": verified_bootstrap_terminal[
                "materialization_terminal_id"
            ],
        }
        if any(final.get(field) != expected for field, expected in predecessor_links.items()):
            _fail("native successor final lost a verified predecessor join")
        anchor = verified_successor.legacy_core_anchor
        anchor_links = {
            key: value for key, value in predecessor_links.items()
            if key not in {
                "legacy_activation_read_only_snapshot_tail_id",
                "legacy_activation_classification_id",
            }
        }
        if any(anchor.get(field) != expected for field, expected in anchor_links.items()):
            _fail("legacy core anchor lost a verified predecessor join")
        successor_roots = successor_documents[SUCCESSOR_EVIDENCE_ROOTS_FILE]
        successor_root_fields = {
            "schema", "schema_version", "predecessor_activation_evidence_root",
            "successor_evidence_root", "predecessor_root_identity_before",
            "predecessor_root_identity_after", "predecessor_inventory_before",
            "predecessor_inventory_after",
            "predecessor_entry_identities_before",
            "predecessor_entry_identities_after",
            "activation_successor_read_only_plan_id",
            "activation_successor_final_evidence_index_id",
            "activation_successor_legacy_core_anchor_id",
            "expected_exact_successor_evidence_names",
            "predecessor_activation_evidence_opened_read_only",
            "predecessor_activation_evidence_mutated",
            "predecessor_all_identities_and_inventory_equal_before_after",
            "successor_evidence_published_o_excl_mode_0400_and_fsynced",
            "legacy_snapshot_or_final_synthesized", "activation_effect_replayed",
            "remote_root_created_or_rebuilt",
        }
        current_predecessor_inventory = pin.inventory()
        before_entries = successor_roots.get(
            "predecessor_entry_identities_before"
        )
        after_entries = successor_roots.get(
            "predecessor_entry_identities_after"
        )
        if (
            set(successor_roots) != successor_root_fields
            or successor_roots.get("schema")
            != successor_finalizer.EVIDENCE_ROOTS_SCHEMA
            or successor_roots.get("schema_version")
            != successor_finalizer.SCHEMA_VERSION
            or successor_roots.get("predecessor_activation_evidence_root")
            != str(predecessor_root)
            or successor_roots.get("successor_evidence_root")
            != str(successor_root)
            or successor_roots.get("predecessor_root_identity_before")
            != successor_roots.get("predecessor_root_identity_after")
            or successor_roots.get("predecessor_inventory_before")
            != current_predecessor_inventory
            or successor_roots.get("predecessor_inventory_after")
            != current_predecessor_inventory
            or type(before_entries) is not dict
            or set(before_entries) != set(current_predecessor_inventory)
            or before_entries != after_entries
            or successor_roots.get("activation_successor_read_only_plan_id")
            != verified_successor.ids[SUCCESSOR_PLAN_FILE]
            or successor_roots.get("activation_successor_final_evidence_index_id")
            != verified_successor.ids[SUCCESSOR_FINAL_FILE]
            or successor_roots.get("activation_successor_legacy_core_anchor_id")
            != verified_successor.ids[LEGACY_CORE_ANCHOR_FILE]
            or successor_roots.get("expected_exact_successor_evidence_names")
            != sorted(successor_finalizer.PUBLICATION_ORDER)
            or successor_roots.get(
                "predecessor_activation_evidence_opened_read_only"
            ) is not True
            or successor_roots.get("predecessor_activation_evidence_mutated")
            is not False
            or successor_roots.get(
                "predecessor_all_identities_and_inventory_equal_before_after"
            ) is not True
            or successor_roots.get(
                "successor_evidence_published_o_excl_mode_0400_and_fsynced"
            ) is not True
            or successor_roots.get("legacy_snapshot_or_final_synthesized")
            is not False
            or successor_roots.get("activation_effect_replayed") is not False
            or successor_roots.get("remote_root_created_or_rebuilt") is not False
        ):
            _fail("successor evidence roots exact contract changed")
        _verify_identity_document(
            successor_roots["predecessor_root_identity_before"],
            os.fstat(pin.descriptor), node_type="DIRECTORY", include_times=False,
            label="successor-indexed predecessor root",
        )
        for name in current_predecessor_inventory:
            observed = os.stat(name, dir_fd=pin.descriptor, follow_symlinks=False)
            _verify_identity_document(
                before_entries[name], observed, node_type="REGULAR_FILE",
                include_times=True,
                label="successor-indexed predecessor entry " + name,
            )
        if (
            verified_activation_terminal["source_manifest_id"]
            != verified_source["source_manifest_id"]
            or verified_activation_terminal["transport_manifest_id"]
            != verified_transport["transport_manifest_id"]
            or verified_activation_terminal["local_materialization_attempt_id"]
            != verified_local_materialization["local_materialization_attempt_id"]
            or verified_activation_terminal["trusted_bootstrap_outer_command"]
            != verified_local_materialization["remote_bootstrap_outer_command"]
            or verified_bootstrap_terminal["source_manifest_id"]
            != verified_source["source_manifest_id"]
            or verified_bootstrap_terminal["transport_manifest_id"]
            != verified_transport["transport_manifest_id"]
        ):
            _fail("activation terminal and nested bootstrap DAG join changed")

        native_inputs = build_native_activation_inputs_v42r3(
            verified_successor=verified_successor,
            materialization_activation_plan=verified_activation_plan,
            predecessor_snapshot_tail_id=previous,
            predecessor_classification=rebuilt_classification,
            predecessor_activation_terminal=verified_activation_terminal,
            preactivation_resource_result=verified_resource_result,
            source_manifest=verified_source,
            transport_manifest=verified_transport,
            local_materialization_attempt=verified_local_materialization,
            remote_materialization_attempt=verified_remote_materialization,
            materialization_terminal=verified_bootstrap_terminal,
        )
        for selected in [pin, *other_pins]:
            selected.verify()
        evidence_identities = {
            "predecessor_activation": pin.identity(),
            "preformal": preformal_pin.identity(),
            "resource": resource_pin.identity(),
            "controls": control_pin.identity(),
        }
        del source_doc, transport_doc, local_materialization_doc, activation_terminal_doc
        return (
            verified_successor, activation_terminal_raw, source_raw,
            transport_raw, native_inputs, evidence_identities,
        )
    finally:
        for selected in reversed(other_pins):
            selected.close()
        pin.close()


def verify_native_formal_inputs_v42r3(
    *, predecessor_activation_evidence_root: Path,
    successor_evidence_root: Path,
    expected_successor_final_evidence_index_id: str,
) -> VerifiedNativeFormalInputsV42r3:
    predecessor_formal_prefix = verify_failed_v42r1_formal_prefix_read_only()
    documents, raws, successor_identity, successor_pin = _read_root_documents(
        successor_evidence_root, SUCCESSOR_FILE_INVENTORY,
        "activation successor evidence root",
    )
    try:
        roots = documents[SUCCESSOR_EVIDENCE_ROOTS_FILE]
        if (
            roots.get("schema")
            != "acfqp.v42_activation_successor_evidence_roots.v42r2"
            or roots.get("predecessor_activation_evidence_root")
            != str(predecessor_activation_evidence_root)
            or roots.get("successor_evidence_root") != str(successor_evidence_root)
            or roots.get("predecessor_activation_evidence_mutated") is not False
            or roots.get("legacy_snapshot_or_final_synthesized") is not False
        ):
            _fail("successor evidence roots index changed")
        (
            verified, activation_raw, source_raw, transport_raw, native_inputs,
            predecessor_identities,
        ) = _verify_predecessor_and_build_native_inputs(
            predecessor_root=predecessor_activation_evidence_root,
            successor_root=successor_evidence_root,
            successor_documents=documents, successor_raws=raws,
            expected_final_evidence_index_id=(
                expected_successor_final_evidence_index_id
            ),
        )
        successor_pin.verify()
        if successor_pin.inventory() != sorted(SUCCESSOR_FILE_INVENTORY):
            _fail("successor evidence inventory changed across predecessor load")
    finally:
        successor_pin.close()
    predecessor_formal_prefix_after = verify_failed_v42r1_formal_prefix_read_only()
    if predecessor_formal_prefix_after != predecessor_formal_prefix:
        _fail("failed V42r1 formal prefix changed across native DAG verification")
    return VerifiedNativeFormalInputsV42r3(
        successor=verified, activation_terminal_raw=activation_raw,
        source_manifest_raw=source_raw, transport_manifest_raw=transport_raw,
        native_activation_inputs=native_inputs,
        predecessor_activation_evidence_root=predecessor_activation_evidence_root,
        successor_evidence_root=successor_evidence_root,
        evidence_root_identities={
            **predecessor_identities, "successor": successor_identity,
        },
        predecessor_formal_prefix=predecessor_formal_prefix,
    )


__all__ = [
    "build_native_activation_inputs_v42r3",
    "VerifiedNativeFormalInputsV42r3",
    "VerifiedSuccessorDocumentsV42r2",
    "V42NativeFormalInputError",
    "verify_native_formal_inputs_v42r3",
    "verify_failed_v42r1_formal_prefix_read_only",
    "verify_successor_documents_v42r2",
]
