from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import stat

import pytest

from acfqp import (
    construction_k7_standard_2048_activation_successor_v42r2 as successor,
)
from acfqp import (
    construction_k7_standard_2048_materialization_activation_v42r1 as activation,
)
from acfqp import (
    construction_k7_standard_2048_remote_execution_authority_v42r1 as authority,
)
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v42_activation_successor_finalizer as finalizer
from scripts import v42_activation_successor_receiver as receiver
from tests.test_construction_k7_standard_2048_materialization_activation_v42r1 import (
    _bootstrap_success_documents,
    _chain,
)


def _fact(relative: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - Git blob identity
            f"blob {len(raw)}\0".encode("ascii") + raw
        ).hexdigest(),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _source_manifest() -> dict[str, object]:
    rows = sorted(
        (
            _fact(successor.SUCCESSOR_LOADER_RELATIVE, b"loader\n"),
            _fact(successor.SUCCESSOR_RECEIVER_RELATIVE, b"receiver\n"),
        ),
        key=lambda row: str(row["relative_path"]),
    )
    return successor.build_activation_successor_source_manifest_v42r2(
        source_commit="1" * 40,
        source_tree="2" * 40,
        source_facts=rows,
    )


def _live_source_manifest() -> dict[str, object]:
    relatives = (
        finalizer.LEGACY_ACTIVATION_DRIVER_RELATIVE,
        successor.SUCCESSOR_LOADER_RELATIVE,
        successor.SUCCESSOR_RECEIVER_RELATIVE,
    )
    rows = [
        _fact(relative, (finalizer.ROOT / relative).read_bytes())
        for relative in relatives
    ]
    return successor.build_activation_successor_source_manifest_v42r2(
        source_commit="4" * 40,
        source_tree="5" * 40,
        source_facts=sorted(rows, key=lambda row: str(row["relative_path"])),
    )


def _receiver_identity(path: str, *, inode: int, mode: int, size: int) -> dict[str, object]:
    return {
        "path": path,
        "node_type": "DIRECTORY" if mode == 0o700 else "REGULAR_FILE",
        "mode": mode,
        "uid": authority.REMOTE_UID,
        "gid": authority.REMOTE_GID,
        "st_dev": 1,
        "st_ino": inode,
        "st_nlink": 2 if mode == 0o700 else 1,
        "st_size": size,
        "st_mtime_ns": 10,
        "st_ctime_ns": 11,
    }


def _raw_receiver_observation(
    observed_documents: dict[str, dict[str, object]],
) -> dict[str, object]:
    fixed = str(authority.REMOTE_ROOT)
    source_root = str(authority.REMOTE_SOURCE_ROOT)
    root_identity = _receiver_identity(fixed, inode=10, mode=0o700, size=4096)
    source_identity = _receiver_identity(
        source_root, inode=11, mode=0o700, size=4096
    )
    role_specs = {
        "source_manifest": (
            "fixed_root", authority.SOURCE_MANIFEST_NAME,
            observed_documents[authority.SOURCE_MANIFEST_NAME],
        ),
        "transport_manifest": (
            "fixed_root", authority.TRANSPORT_MANIFEST_NAME,
            observed_documents[authority.TRANSPORT_MANIFEST_NAME],
        ),
        "local_materialization_attempt": (
            "fixed_root", authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            observed_documents[authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME],
        ),
        "remote_materialization_attempt": (
            "fixed_root", authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
            observed_documents[authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME],
        ),
        "materialization_terminal": (
            "source_root", authority.MATERIALIZATION_TERMINAL_NAME,
            observed_documents[authority.MATERIALIZATION_TERMINAL_NAME],
        ),
    }
    documents: dict[str, object] = {}
    for index, (role, (parent, name, document)) in enumerate(
        role_specs.items(), start=20
    ):
        parent_path = fixed if parent == "fixed_root" else source_root
        raw = canonical_json_bytes(document)
        identity = _receiver_identity(
            parent_path + "/" + name,
            inode=index,
            mode=0o400,
            size=len(raw),
        )
        documents[role] = {
            "absolute_path": parent_path + "/" + name,
            "relative_name": name,
            "identity_before": identity,
            "identity_opened": identity,
            "identity_after": identity,
            "byte_count": len(raw),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "document": document,
            "parent": parent,
        }
    root_inventory = sorted(
        [
            authority.SOURCE_MANIFEST_NAME,
            authority.TRANSPORT_MANIFEST_NAME,
            authority.LOCAL_MATERIALIZATION_ATTEMPT_NAME,
            authority.REMOTE_MATERIALIZATION_ATTEMPT_NAME,
            authority.REMOTE_SOURCE_ROOT.name,
        ]
    )
    source_inventory = [authority.MATERIALIZATION_TERMINAL_NAME]
    payload = {
        "schema": receiver.OBSERVATION_SCHEMA,
        "schema_version": receiver.SCHEMA_VERSION,
        "formal_identity": authority.FORMAL_IDENTITY,
        "global_execution_ordinal": authority.GLOBAL_EXECUTION_ORDINAL,
        "observed_hostname": authority.REMOTE_HOSTNAME,
        "observed_user": authority.REMOTE_USER,
        "observed_uid": authority.REMOTE_UID,
        "observed_gid": authority.REMOTE_GID,
        "fixed_root_lexical_chain_before": [],
        "fixed_root_lexical_chain_after": [],
        "fixed_root": {
            "path": fixed,
            "identity_before": root_identity,
            "identity_opened": root_identity,
            "identity_after": root_identity,
            "inventory_before": root_inventory,
            "inventory_after": root_inventory,
        },
        "source_root": {
            "path": source_root,
            "identity_before": source_identity,
            "identity_opened": source_identity,
            "identity_after": source_identity,
            "inventory_before": source_inventory,
            "inventory_after": source_inventory,
        },
        "documents": documents,
        "single_pinned_before_after_window": True,
        "all_document_reads_nofollow_and_stable": True,
        "collected_subset_only_not_whole_tree": True,
        "large_binary_content_read": False,
        "observed_document_count": 5,
        "remote_mutation_performed": False,
        "only_fixed_small_json_documents_read": True,
    }
    return {
        **payload,
        "activation_successor_read_only_observation_id": hashlib.sha256(
            receiver.OBSERVATION_ID_DOMAIN.encode("ascii")
            + b"\0"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _legacy_snapshot(plan: dict[str, object], terminal_id: str) -> dict[str, object]:
    classification_payload = {
        "schema": activation.MATERIALIZATION_ACTIVATION_CLASSIFICATION_SCHEMA,
        "materialization_activation_plan_id": plan[
            "materialization_activation_plan_id"
        ],
        "classification": activation.CLASSIFICATION_SUCCESS,
        "remote_materialization_transport_terminal_id": terminal_id,
        "activation_retry_authorized": False,
        "remote_mutation_performed_by_classifier": False,
    }
    classification = {
        **classification_payload,
        "materialization_activation_classification_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:materialization-activation-classification\0"
            + canonical_json_bytes(classification_payload)
        ).hexdigest(),
    }
    payload = {
        "schema": "acfqp.v42_materialization_activation_read_only_snapshot.v42r1",
        "materialization_activation_plan_id": plan[
            "materialization_activation_plan_id"
        ],
        "snapshot_ordinal": 1,
        "previous_snapshot_id": None,
        "observation": {"offline_successor_fixture": True},
        "classification": classification,
        "remote_observation_only": True,
        "activation_effect_replay_authorized": False,
    }
    return {
        **payload,
        "activation_read_only_snapshot_id": hashlib.sha256(
            b"acfqp:v42-remote-ordinal2:activation-read-only-snapshot\0"
            + canonical_json_bytes(payload)
        ).hexdigest(),
    }


def _publish_fixture(path: Path, document: dict[str, object]) -> None:
    path.write_bytes(canonical_json_bytes(document))
    path.chmod(0o400)


def _bind_live_legacy_driver(plan: dict[str, object]) -> dict[str, object]:
    result = copy.deepcopy(plan)
    raw = (
        finalizer.ROOT / finalizer.LEGACY_ACTIVATION_DRIVER_RELATIVE
    ).read_bytes()
    artifact = result["activation_driver_artifact"]
    assert isinstance(artifact, dict)
    artifact.update(_fact(finalizer.LEGACY_ACTIVATION_DRIVER_RELATIVE, raw))
    payload = dict(result)
    payload.pop("materialization_activation_plan_id", None)
    result["materialization_activation_plan_id"] = hashlib.sha256(
        b"acfqp:v42-remote-ordinal2:materialization-activation-plan\0"
        + canonical_json_bytes(payload)
    ).hexdigest()
    return result


def test_local_attempt_and_network_start_are_content_addressed_no_effects() -> None:
    plan = {"activation_successor_read_only_plan_id": "3" * 64}
    source = _source_manifest()
    attempt = finalizer.build_local_attempt_v42r2(
        successor_plan=plan, controller_source_manifest=source
    )
    start = finalizer.build_network_start_v42r2(
        successor_plan=plan, local_attempt=attempt
    )
    assert finalizer.verify_local_attempt_v42r2(
        attempt, successor_plan=plan, controller_source_manifest=source
    ) == attempt
    assert finalizer.verify_network_start_v42r2(
        start, successor_plan=plan, local_attempt=attempt
    ) == start
    assert attempt["activation_effect_replay_authorized"] is False
    assert attempt["remote_root_creation_or_rebuild_authorized"] is False
    assert start["remote_filesystem_mutation_authorized"] is False
    assert start["additional_or_durable_remote_process_authorized"] is False


def test_successor_journal_is_sibling_o_excl_mode_0400_and_idempotent(
    tmp_path: Path,
) -> None:
    os.chmod(tmp_path, 0o755)
    predecessor = tmp_path / ".acfqp-v42-local-activation-evidence-a"
    successor_root = tmp_path / (
        finalizer.SUCCESSOR_ROOT_PREFIX + "b" * 64
    )
    journal = finalizer._SuccessorJournal.open_or_create(  # noqa: SLF001
        successor_root, predecessor_root=predecessor
    )
    try:
        document = {"schema": "test.successor", "value": 1}
        journal.publish_or_verify("ONE.json", document)
        journal.publish_or_verify("ONE.json", document)
        observed = (successor_root / "ONE.json").lstat()
        assert stat.S_IMODE(observed.st_mode) == 0o400
        assert observed.st_nlink == 1
        with pytest.raises(
            finalizer.V42ActivationSuccessorFinalizerError,
            match="retained successor artifact changed",
        ):
            journal.publish_or_verify(
                "ONE.json", {"schema": "test.successor", "value": 2}
            )
        journal.verify_unique_files()
    finally:
        journal.close()
    assert stat.S_IMODE(successor_root.lstat().st_mode) == 0o700


def test_successor_journal_rejects_non_sibling_and_symlink_root(
    tmp_path: Path,
) -> None:
    os.chmod(tmp_path, 0o755)
    predecessor = tmp_path / ".acfqp-v42-local-activation-evidence-a"
    outside = tmp_path / "nested"
    outside.mkdir(mode=0o755)
    with pytest.raises(
        finalizer.V42ActivationSuccessorFinalizerError,
        match="exact sibling",
    ):
        finalizer._SuccessorJournal.open_or_create(  # noqa: SLF001
            outside / (finalizer.SUCCESSOR_ROOT_PREFIX + "c" * 64),
            predecessor_root=predecessor,
        )
    target = tmp_path / "real"
    target.mkdir(mode=0o700)
    redirected = tmp_path / (finalizer.SUCCESSOR_ROOT_PREFIX + "d" * 64)
    redirected.symlink_to(target, target_is_directory=True)
    with pytest.raises((OSError, finalizer.V42ActivationSuccessorFinalizerError)):
        finalizer._SuccessorJournal.open_or_create(  # noqa: SLF001
            redirected, predecessor_root=predecessor
        )


def test_runner_defines_no_legacy_snapshot_or_final_publication_name() -> None:
    names = {
        finalizer.CONTROLLER_SOURCE_MANIFEST_NAME,
        finalizer.PLAN_NAME,
        finalizer.LOCAL_ATTEMPT_NAME,
        finalizer.NETWORK_START_NAME,
        finalizer.RECEIVER_OBSERVATION_NAME,
        finalizer.OBSERVATION_NAME,
        finalizer.PATH_RECEIPT_NAME,
        finalizer.CLASSIFICATION_NAME,
        finalizer.SNAPSHOT_NAME,
        finalizer.OBSERVED_REMOTE_ATTEMPT_NAME,
        finalizer.OBSERVED_SOURCE_TERMINAL_NAME,
        finalizer.FINAL_INDEX_NAME,
        finalizer.LEGACY_CORE_ANCHOR_NAME,
        finalizer.EVIDENCE_ROOTS_NAME,
    }
    assert "MATERIALIZATION_ACTIVATION_FINAL_EVIDENCE_INDEX.json" not in names
    assert not any(name.startswith("ACTIVATION_READ_ONLY_SNAPSHOT_") for name in names)


def test_offline_orchestration_builds_native_chain_and_resume_does_not_redispatch(
    tmp_path: Path,
) -> None:
    os.chmod(tmp_path, 0o755)
    chain = _chain()
    legacy_plan = _bind_live_legacy_driver(chain["activation_plan"])
    predecessor = tmp_path / ".acfqp-v42-local-activation-evidence-offline"
    predecessor.mkdir(mode=0o700)
    _publish_fixture(
        predecessor / finalizer.PREDECESSOR_PLAN_NAME, legacy_plan
    )
    legacy_snapshot = _legacy_snapshot(
        legacy_plan,
        chain["terminal"]["remote_materialization_transport_terminal_id"],
    )
    _publish_fixture(
        predecessor / "ACTIVATION_READ_ONLY_SNAPSHOT_00000001.json",
        legacy_snapshot,
    )
    predecessor_before = {
        path.name: (path.read_bytes(), path.lstat())
        for path in predecessor.iterdir()
    }
    successor_root = tmp_path / (finalizer.SUCCESSOR_ROOT_PREFIX + "6" * 64)
    raw_observation = _raw_receiver_observation(
        _bootstrap_success_documents(chain)
    )
    calls: list[dict[str, object]] = []

    def dispatch(**arguments: object) -> dict[str, object]:
        envelope = arguments["envelope"]
        assert isinstance(envelope, dict)
        assert set(envelope) == {
            "schema", "operation", "activation_successor_read_only_plan"
        }
        assert envelope["schema"] == finalizer.INGRESS_SCHEMA
        assert envelope["operation"] == finalizer.INGRESS_OPERATION
        assert arguments["receiver_raw"] == (
            finalizer.ROOT / successor.SUCCESSOR_RECEIVER_RELATIVE
        ).read_bytes()
        argv = arguments["argv"]
        assert isinstance(argv, list) and len(argv) == 45
        calls.append(arguments)
        return raw_observation

    arguments = {
        "predecessor_activation_evidence_root": predecessor,
        "successor_evidence_root": successor_root,
        "expected_legacy_activation_plan_id": legacy_plan[
            "materialization_activation_plan_id"
        ],
        "controller_source_manifest": _live_source_manifest(),
        "dispatch": dispatch,
    }
    first = finalizer.orchestrate_activation_successor_v42r2(**arguments)
    second = finalizer.orchestrate_activation_successor_v42r2(**arguments)
    assert first == second
    assert len(calls) == 1
    assert first["remote_observation_only"] is True
    assert first["activation_effect_replayed"] is False
    assert first["legacy_activation_snapshot_or_final_synthesized"] is False
    assert sorted(path.name for path in successor_root.iterdir()) == sorted(
        finalizer.PUBLICATION_ORDER
    )
    for path in successor_root.iterdir():
        observed = path.lstat()
        assert stat.S_IMODE(observed.st_mode) == 0o400
        assert observed.st_nlink == 1
    assert finalizer.PREDECESSOR_FINAL_NAME not in {
        path.name for path in predecessor.iterdir()
    }
    for path in predecessor.iterdir():
        raw, observed = predecessor_before[path.name]
        current = path.lstat()
        assert path.read_bytes() == raw
        assert (
            current.st_dev, current.st_ino, current.st_mode, current.st_uid,
            current.st_gid, current.st_nlink, current.st_size,
            current.st_mtime_ns, current.st_ctime_ns,
        ) == (
            observed.st_dev, observed.st_ino, observed.st_mode,
            observed.st_uid, observed.st_gid, observed.st_nlink,
            observed.st_size, observed.st_mtime_ns, observed.st_ctime_ns,
        )
