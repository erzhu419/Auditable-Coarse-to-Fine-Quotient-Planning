from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from types import ModuleType
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v42_standard_2048_formal_transport_successor_driver as driver


def _fact(relative: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative,
        "git_mode": "100644",
        "git_object_type": "blob",
        "git_blob_oid": hashlib.sha1(  # noqa: S324 - exact Git identity
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest(),
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _pure_chain_fixture() -> tuple[
    dict[str, dict[str, Any]], dict[str, bytes], dict[str, bytes],
]:
    program_raws = {
        relative: ("# " + relative + "\n").encode("utf-8")
        for relative in driver.SUCCESSOR_CONTROLLER_TCB_PATHS
    }
    source = {
        "activation_successor_source_manifest_id": "1" * 64,
        "source_commit": "a" * 40,
        "source_tree": "b" * 40,
        "source_facts": [
            _fact(relative, program_raws[relative])
            for relative in sorted(program_raws)
        ],
    }
    plan = {"activation_successor_read_only_plan_id": "2" * 64}
    local = {"activation_successor_local_read_only_attempt_id": "3" * 64}
    network = {"activation_successor_read_only_network_start_id": "4" * 64}
    receiver = {"activation_successor_read_only_observation_id": "5" * 64}
    receipt = {"activation_successor_path_provenance_receipt_id": "6" * 64}
    remote = {"kind": "remote-materialization-attempt"}
    terminal = {"kind": "nested-source-terminal"}
    observation = {
        "activation_successor_observation_id": "7" * 64,
        "documents": {
            driver.successor.REMOTE_ATTEMPT_RELATIVE_PATH: remote,
            driver.successor.SOURCE_TERMINAL_RELATIVE_PATH: terminal,
        },
    }
    classification = {"activation_successor_classification_id": "8" * 64}
    snapshot = {"activation_successor_read_only_snapshot_id": "9" * 64}
    final = {"activation_successor_final_evidence_index_id": "a" * 64}
    anchor = {"activation_successor_legacy_core_anchor_id": "b" * 64}
    roots = {"schema": "acfqp.v42_activation_successor_evidence_roots.v42r2"}
    documents = {
        driver.SUCCESSOR_SOURCE_MANIFEST_FILE: source,
        driver.SUCCESSOR_PLAN_FILE: plan,
        driver.SUCCESSOR_LOCAL_ATTEMPT_FILE: local,
        driver.SUCCESSOR_NETWORK_START_FILE: network,
        driver.SUCCESSOR_RECEIVER_OBSERVATION_FILE: receiver,
        driver.SUCCESSOR_PATH_RECEIPT_FILE: receipt,
        driver.SUCCESSOR_OBSERVATION_FILE: observation,
        driver.SUCCESSOR_CLASSIFICATION_FILE: classification,
        driver.SUCCESSOR_SNAPSHOT_FILE: snapshot,
        driver.OBSERVED_REMOTE_ATTEMPT_FILE: remote,
        driver.OBSERVED_SOURCE_TERMINAL_FILE: terminal,
        driver.SUCCESSOR_FINAL_FILE: final,
        driver.LEGACY_CORE_ANCHOR_FILE: anchor,
        driver.SUCCESSOR_EVIDENCE_ROOTS_FILE: roots,
    }
    return (
        documents,
        {name: canonical_json_bytes(value) for name, value in documents.items()},
        program_raws,
    )


def _legacy_plan_with_dispatch_fact(
    program_raws: dict[str, bytes],
) -> dict[str, object]:
    relative = driver.successor_finalizer.LEGACY_ACTIVATION_DRIVER_RELATIVE
    return {
        "activation_driver_artifact": {
            **_fact(relative, program_raws[relative]),
            "file_mode": "0444",
            "committed_regular_file_required": True,
        }
    }


def _install_pure_verifier_stubs(
    monkeypatch: pytest.MonkeyPatch,
    *, documents: dict[str, dict[str, Any]],
    program_raws: dict[str, bytes],
) -> list[str]:
    events: list[str] = []

    def record(name: str, value: dict[str, Any]):
        def selected(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
            events.append(name)
            return value

        return selected

    source = documents[driver.SUCCESSOR_SOURCE_MANIFEST_FILE]
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_source_manifest_v42r2",
        record("source", source),
    )
    monkeypatch.setattr(driver, "_frozen_git_primitives", lambda: {})
    monkeypatch.setattr(
        driver.legacy, "_early_git_tree",
        lambda **_kwargs: {
            relative: (
                fact["git_mode"], fact["git_object_type"], fact["git_blob_oid"]
            )
            for relative, fact in {
                row["relative_path"]: row for row in source["source_facts"]
            }.items()
        },
    )
    monkeypatch.setattr(
        driver.legacy, "_program_raw", lambda relative: program_raws[relative]
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_read_only_plan_v42r2",
        record("plan", documents[driver.SUCCESSOR_PLAN_FILE]),
    )
    monkeypatch.setattr(
        driver.successor_finalizer, "verify_local_attempt_v42r2",
        record("local", documents[driver.SUCCESSOR_LOCAL_ATTEMPT_FILE]),
    )
    monkeypatch.setattr(
        driver.successor_finalizer, "verify_network_start_v42r2",
        record("network", documents[driver.SUCCESSOR_NETWORK_START_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_receiver_observation_v42r2",
        record("receiver", documents[driver.SUCCESSOR_RECEIVER_OBSERVATION_FILE]),
    )
    monkeypatch.setattr(
        driver.successor,
        "verify_activation_successor_path_provenance_receipt_v42r2",
        record("path", documents[driver.SUCCESSOR_PATH_RECEIPT_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "build_activation_successor_observation_v42r2",
        record("normalize", documents[driver.SUCCESSOR_OBSERVATION_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_observation_v42r2",
        record("observation", documents[driver.SUCCESSOR_OBSERVATION_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_classification_v42r2",
        record("classification", documents[driver.SUCCESSOR_CLASSIFICATION_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_snapshot_v42r2",
        record("snapshot", documents[driver.SUCCESSOR_SNAPSHOT_FILE]),
    )
    monkeypatch.setattr(
        driver.successor,
        "verify_activation_successor_final_evidence_index_v42r2",
        record("final", documents[driver.SUCCESSOR_FINAL_FILE]),
    )
    monkeypatch.setattr(
        driver.successor, "verify_activation_successor_legacy_core_anchor_v42r2",
        record("anchor", documents[driver.LEGACY_CORE_ANCHOR_FILE]),
    )
    return events


def test_direct_adapter_entry_fails_before_effectful_main() -> None:
    completed = subprocess.run(
        [sys.executable, str(Path(driver.__file__).resolve()), "--prepare-once"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=10.0,
    )
    assert completed.returncode != 0
    assert completed.stdout == b""
    assert (
        b"must be imported by the verified activation-successor launcher"
        in completed.stderr
    )


def test_successor_tcb_inventory_matches_verified_launcher_exactly() -> None:
    from scripts import (  # noqa: PLC0415
        launch_v42_activation_successor_or_formal as launcher,
    )

    assert len(launcher.TCB_PATHS) == 27
    assert launcher.TCB_PATHS == tuple(sorted(launcher.TCB_PATHS))
    assert driver.SUCCESSOR_CONTROLLER_TCB_PATHS == frozenset(launcher.TCB_PATHS)
    assert set(driver.SUCCESSOR_FILE_INVENTORY) == set(
        driver.successor_finalizer.PUBLICATION_ORDER
    )


def test_successor_documents_delegate_complete_pure_chain_and_nested_raws(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    documents, raws, program_raws = _pure_chain_fixture()
    events = _install_pure_verifier_stubs(
        monkeypatch, documents=documents, program_raws=program_raws
    )
    verified = driver.verify_successor_documents_v42r2(
        documents=documents,
        raws=raws,
        expected_final_evidence_index_id="a" * 64,
        legacy_activation_plan=_legacy_plan_with_dispatch_fact(program_raws),
        legacy_snapshot_tail={"legacy": "snapshot-tail"},
        preactivation_resource_result_id="c" * 64,
        successor_evidence_root=tmp_path,
        loader_source_raw=program_raws[driver.successor.SUCCESSOR_LOADER_RELATIVE],
        receiver_source_raw=program_raws[
            driver.successor.SUCCESSOR_RECEIVER_RELATIVE
        ],
    )
    assert events == [
        "source", "plan", "local", "network", "receiver", "path",
        "normalize", "observation", "classification", "snapshot", "final",
        "anchor",
    ]
    assert verified.ids[driver.SUCCESSOR_FINAL_FILE] == "a" * 64
    assert verified.ids[driver.LEGACY_CORE_ANCHOR_FILE] == "b" * 64


def test_frozen_git_primitive_cache_is_reentrant_but_rejects_preload_or_swap(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module_name = driver._FROZEN_GIT_MODULE_NAME  # noqa: SLF001
    monkeypatch.setattr(driver, "_FROZEN_GIT_MODULE", None)
    monkeypatch.setattr(driver, "_FROZEN_GIT_PRIMITIVES", None)
    monkeypatch.setitem(driver.sys.modules, module_name, ModuleType(module_name))
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError, match="before adapter-owned"
    ):
        driver._frozen_git_primitives()  # noqa: SLF001

    monkeypatch.delitem(driver.sys.modules, module_name)
    namespace = {
        "_run_fixed_git_v42r1": object(),
        "_open_absolute_directory_chain": object(),
        "_read_relative_tcb_file_v42r1": object(),
        "GIT_VERSION_STDOUT": b"git version test\n",
    }

    def load() -> dict[str, object]:
        module = ModuleType(module_name)
        module.__dict__.update(namespace)
        driver.sys.modules[module_name] = module
        return module.__dict__

    monkeypatch.setattr(driver.legacy, "_frozen_launcher_primitives", load)
    first = driver._frozen_git_primitives()  # noqa: SLF001
    second = driver._frozen_git_primitives()  # noqa: SLF001
    assert first is second
    driver.sys.modules[module_name] = ModuleType(module_name)
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError, match="changed after"
    ):
        driver._frozen_git_primitives()  # noqa: SLF001


def test_nested_observed_copy_drift_fails_after_path_receipt_verification(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    documents, raws, program_raws = _pure_chain_fixture()
    events = _install_pure_verifier_stubs(
        monkeypatch, documents=documents, program_raws=program_raws
    )
    changed = {"kind": "top-level-terminal-copy"}
    documents[driver.OBSERVED_SOURCE_TERMINAL_FILE] = changed
    raws[driver.OBSERVED_SOURCE_TERMINAL_FILE] = canonical_json_bytes(changed)
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError,
        match="lost path-receipt bytes",
    ):
        driver.verify_successor_documents_v42r2(
            documents=documents, raws=raws,
            expected_final_evidence_index_id="a" * 64,
            legacy_activation_plan=_legacy_plan_with_dispatch_fact(program_raws),
            legacy_snapshot_tail={},
            preactivation_resource_result_id="c" * 64,
            successor_evidence_root=tmp_path,
            loader_source_raw=program_raws[
                driver.successor.SUCCESSOR_LOADER_RELATIVE
            ],
            receiver_source_raw=program_raws[
                driver.successor.SUCCESSOR_RECEIVER_RELATIVE
            ],
        )
    assert "path" in events and "final" in events and "anchor" in events


def test_legacy_dispatch_driver_must_join_source_manifest_before_plan_verify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    documents, raws, program_raws = _pure_chain_fixture()
    events = _install_pure_verifier_stubs(
        monkeypatch, documents=documents, program_raws=program_raws
    )
    legacy_plan = _legacy_plan_with_dispatch_fact(program_raws)
    legacy_plan["activation_driver_artifact"] = {
        **legacy_plan["activation_driver_artifact"],
        "sha256": "0" * 64,
    }
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError,
        match="differs between retained activation plan",
    ):
        driver.verify_successor_documents_v42r2(
            documents=documents,
            raws=raws,
            expected_final_evidence_index_id="a" * 64,
            legacy_activation_plan=legacy_plan,
            legacy_snapshot_tail={},
            preactivation_resource_result_id="c" * 64,
            successor_evidence_root=tmp_path,
            loader_source_raw=program_raws[
                driver.successor.SUCCESSOR_LOADER_RELATIVE
            ],
            receiver_source_raw=program_raws[
                driver.successor.SUCCESSOR_RECEIVER_RELATIVE
            ],
        )
    assert events == ["source"]


def test_predecessor_legacy_final_is_rejected_without_being_read(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    events: list[str] = []

    class FinalOnlyPin:
        def inventory(self) -> list[str]:
            events.append("inventory")
            return [driver.legacy.ACTIVATION_FINAL_EVIDENCE_INDEX_FILE]

        def read(self, *_args: Any, **_kwargs: Any) -> bytes:
            return pytest.fail("legacy final must never be read")

        def close(self) -> None:
            events.append("close")

    monkeypatch.setattr(
        driver.legacy._EvidenceRootPin,  # noqa: SLF001
        "open",
        lambda *_args, **_kwargs: FinalOnlyPin(),
    )
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError,
        match="unexpectedly contains a legacy final",
    ):
        driver._verify_predecessor_and_build_core(  # noqa: SLF001
            predecessor_root=tmp_path / "predecessor",
            successor_root=tmp_path / "successor",
            successor_documents={},
            successor_raws={},
            expected_final_evidence_index_id="a" * 64,
        )
    assert events == ["inventory", "close"]


def _verified_for_persistence(tmp_path: Path) -> driver.VerifiedSuccessorActivationV42r2:
    successor_documents = driver.VerifiedSuccessorDocumentsV42r2(
        documents={}, raws={},
        ids={
            driver.SUCCESSOR_FINAL_FILE: "a" * 64,
            driver.LEGACY_CORE_ANCHOR_FILE: "b" * 64,
        },
        final={"activation_successor_final_evidence_index_id": "a" * 64},
        legacy_core_anchor={
            "activation_successor_legacy_core_anchor_id": "b" * 64
        },
    )
    return driver.VerifiedSuccessorActivationV42r2(
        successor=successor_documents,
        activation_terminal_raw=b'{"terminal":true}',
        source_manifest_raw=b"{}", transport_manifest_raw=b"{}",
        production_activation_core={"production_activation_core_id": "c" * 64},
        predecessor_activation_evidence_root=tmp_path / "predecessor",
        successor_evidence_root=tmp_path / "successor",
        evidence_root_identities={"successor": {"st_ino": 1}},
    )


def test_plan_prefix_writes_native_bridge_assembly_but_no_legacy_final(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    journal = tmp_path / "formal"
    monkeypatch.setattr(driver.formal, "LOCAL_FORMAL_JOURNAL_ROOT", journal)
    writes: dict[str, bytes] = {}
    monkeypatch.setattr(
        driver.legacy, "_publish_or_verify",
        lambda path, raw: writes.__setitem__(path.name, raw),
    )
    verified = _verified_for_persistence(tmp_path)
    plan = {"formal_transport_plan_id": "d" * 64}
    driver._persist_successor_plan_prefix(  # noqa: SLF001
        plan=plan, activation_raw=verified.activation_terminal_raw,
        verified=verified,
    )
    assert set(writes) == {
        driver.formal.LOCAL_PLAN_NAME,
        driver.formal.LOCAL_ACTIVATION_TERMINAL_NAME,
        driver.FORMAL_SUCCESSOR_EVIDENCE_ASSEMBLY_FILE,
    }
    assert driver.legacy.ACTIVATION_FINAL_EVIDENCE_INDEX_FILE not in writes
    assert not any(
        name.startswith(driver.legacy.ACTIVATION_READ_ONLY_SNAPSHOT_PREFIX)
        for name in writes
    )
    assembly = driver.loads_canonical_json(
        writes[driver.FORMAL_SUCCESSOR_EVIDENCE_ASSEMBLY_FILE]
    )
    assert assembly["activation_successor_final_evidence_index_id"] == "a" * 64
    assert assembly["activation_successor_legacy_core_anchor_id"] == "b" * 64
    assert assembly["legacy_snapshot_or_final_synthesized"] is False


def test_bad_successor_evidence_cannot_create_formal_journal(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    predecessor = tmp_path / "predecessor"
    successor_root = tmp_path / "successor"
    events: list[str] = []

    def reject(**_kwargs: Any) -> None:
        events.append("verify")
        raise driver.V42FormalTransportSuccessorDriverError("bad successor")

    monkeypatch.setattr(driver, "verify_successor_activation_evidence_v42r2", reject)
    monkeypatch.setattr(
        driver.legacy, "_ensure_journal_root", lambda: events.append("journal")
    )
    with pytest.raises(
        driver.V42FormalTransportSuccessorDriverError, match="bad successor"
    ):
        driver.main(
            [
                "--predecessor-activation-evidence-root", str(predecessor),
                "--successor-evidence-root", str(successor_root),
                "--expected-successor-final-evidence-index-id", "a" * 64,
                "--probe-host-epoch",
            ]
        )
    assert events == ["verify"]


@pytest.mark.parametrize(
    "extra",
    [
        ["--inspection-ordinal", "0"],
        ["--inspection-ordinal", "2"],
    ],
)
def test_direct_cli_rejects_invalid_or_noninspection_ordinal_before_verify(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, extra: list[str],
) -> None:
    monkeypatch.setattr(
        driver, "verify_successor_activation_evidence_v42r2",
        lambda **_kwargs: pytest.fail("evidence verifier must remain unreachable"),
    )
    with pytest.raises(driver.V42FormalTransportSuccessorDriverError):
        driver.main(
            [
                "--predecessor-activation-evidence-root", str(tmp_path / "old"),
                "--successor-evidence-root", str(tmp_path / "new"),
                "--expected-successor-final-evidence-index-id", "a" * 64,
                "--prepare-once", *extra,
            ]
        )


def test_prepare_mode_delegates_to_frozen_one_shot_machine(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    verified = _verified_for_persistence(tmp_path)
    events: list[str] = []
    monkeypatch.setattr(
        driver, "verify_successor_activation_evidence_v42r2",
        lambda **_kwargs: verified,
    )
    monkeypatch.setattr(driver.legacy, "_ensure_journal_root", lambda: None)
    monkeypatch.setattr(driver.legacy, "_publish_or_verify", lambda *_args: None)
    monkeypatch.setattr(
        driver.legacy, "_load_epoch_or_probe", lambda **_kwargs: {"epoch": True}
    )
    monkeypatch.setattr(
        driver, "_build_successor_formal_plan",
        lambda **_kwargs: (
            {"formal_transport_plan_id": "d" * 64},
            verified.activation_terminal_raw,
            verified.production_activation_core,
        ),
    )
    monkeypatch.setattr(
        driver, "_persist_successor_plan_prefix",
        lambda **_kwargs: events.append("persist"),
    )
    monkeypatch.setattr(
        driver.legacy, "execute_prepare_once_v42r1",
        lambda _plan: events.append("legacy-prepare") or {"receipt": {}},
    )
    assert driver.main(
        [
            "--predecessor-activation-evidence-root",
            str(verified.predecessor_activation_evidence_root),
            "--successor-evidence-root", str(verified.successor_evidence_root),
            "--expected-successor-final-evidence-index-id", "a" * 64,
            "--prepare-once",
        ]
    ) == 0
    assert events == ["persist", "legacy-prepare"]


def test_inspect_launch_reads_retained_attempt_without_replaying_effect(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    verified = _verified_for_persistence(tmp_path)
    events: list[object] = []
    plan = {"formal_transport_plan_id": "d" * 64}
    retained_prepare_receipt = {"formal_prepare_receipt_id": "e" * 64}
    local_attempt_id = "f" * 64
    monkeypatch.setattr(
        driver, "verify_successor_activation_evidence_v42r2",
        lambda **_kwargs: verified,
    )
    monkeypatch.setattr(driver.legacy, "_ensure_journal_root", lambda: None)
    monkeypatch.setattr(driver.legacy, "_publish_or_verify", lambda *_args: None)
    monkeypatch.setattr(
        driver.legacy, "_load_epoch_or_probe", lambda **_kwargs: {"epoch": True}
    )
    monkeypatch.setattr(
        driver, "_build_successor_formal_plan",
        lambda **_kwargs: (
            plan,
            verified.activation_terminal_raw,
            verified.production_activation_core,
        ),
    )
    monkeypatch.setattr(
        driver, "_persist_successor_plan_prefix",
        lambda **_kwargs: events.append("persist"),
    )
    monkeypatch.setattr(
        driver.legacy, "execute_prepare_once_v42r1",
        lambda *_args, **_kwargs: pytest.fail("prepare effect must not replay"),
    )
    monkeypatch.setattr(
        driver.legacy, "execute_launch_admission_once_v42r1",
        lambda *_args, **_kwargs: pytest.fail("launch effect must not replay"),
    )
    monkeypatch.setattr(
        driver.legacy, "_retained_prepare",
        lambda _plan: (retained_prepare_receipt, b"retained-prepare"),
    )
    monkeypatch.setattr(
        driver.legacy, "_stable_read", lambda *_args, **_kwargs: b"local-attempt"
    )
    monkeypatch.setattr(
        driver.authority, "verify_local_launch_attempt_v42r1",
        lambda raw, *, prepare_receipt: (
            {"local_launch_attempt_id": local_attempt_id}
            if raw == b"local-attempt"
            and prepare_receipt == retained_prepare_receipt
            else pytest.fail("retained launch join changed")
        ),
    )
    inspection = {"read_only": True}
    monkeypatch.setattr(
        driver.legacy, "inspect_read_only_v42r1",
        lambda **kwargs: events.append(("inspect", kwargs)) or inspection,
    )
    monkeypatch.setattr(
        driver.legacy, "classify_after_inspection_v42r1",
        lambda **kwargs: events.append(("classify", kwargs)),
    )
    assert driver.main(
        [
            "--predecessor-activation-evidence-root",
            str(verified.predecessor_activation_evidence_root),
            "--successor-evidence-root", str(verified.successor_evidence_root),
            "--expected-successor-final-evidence-index-id", "a" * 64,
            "--inspect-launch", "--inspection-ordinal", "2",
        ]
    ) == 0
    assert events[0] == "persist"
    assert events[1] == (
        "inspect",
        {
            "plan": plan,
            "operation": driver.formal.OPERATION_LAUNCH,
            "attempt_id": local_attempt_id,
            "ordinal": 2,
        },
    )
    assert events[2] == (
        "classify",
        {
            "plan": plan,
            "operation": driver.formal.OPERATION_LAUNCH,
            "attempt_id": local_attempt_id,
            "ordinal": 2,
            "inspection": inspection,
        },
    )
