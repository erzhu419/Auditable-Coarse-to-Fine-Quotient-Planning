from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from scripts import (
    run_v42_standard_2048_formal_transport_native_successor_driver as native,
)


HEX = {
    name: format(index, "064x")
    for index, name in enumerate(
        (
            native.SUCCESSOR_SOURCE_MANIFEST_FILE,
            native.SUCCESSOR_PLAN_FILE,
            native.SUCCESSOR_PATH_RECEIPT_FILE,
            native.SUCCESSOR_CLASSIFICATION_FILE,
            native.SUCCESSOR_SNAPSHOT_FILE,
            native.SUCCESSOR_FINAL_FILE,
            native.LEGACY_CORE_ANCHOR_FILE,
        ),
        start=1,
    )
}


def _verified_successor() -> native.VerifiedSuccessorDocumentsV42r2:
    plan = {
        "fixed_remote_root": "/remote/root",
        "remote_source_root": "/remote/root/source",
        "remote_target_alias": "jtl110gpu2",
        "expected_remote_hostname": "erzhu419-Super-Server",
    }
    receipt = {
        "observed_hostname": "erzhu419-Super-Server",
        "observed_user": "erzhu419",
        "observed_uid": 1000,
        "observed_gid": 1000,
    }
    final = {
        "formal_identity": "STANDARD_2048_FRESH_TERMINAL_V42_REMOTE_ORDINAL_2",
        "global_execution_ordinal": 2,
    }
    return native.VerifiedSuccessorDocumentsV42r2(
        documents={
            native.SUCCESSOR_PLAN_FILE: plan,
            native.SUCCESSOR_PATH_RECEIPT_FILE: receipt,
        },
        raws={},
        ids=HEX,
        final=final,
        legacy_core_anchor={"compatibility_only": True},
    )


def test_native_projection_keeps_compatibility_anchor_non_authoritative() -> None:
    projected = native.build_native_activation_inputs_v42r3(
        verified_successor=_verified_successor(),
        materialization_activation_plan={
            "materialization_activation_plan_id": "a" * 64
        },
        predecessor_snapshot_tail_id="b" * 64,
        predecessor_classification={
            "materialization_activation_classification_id": "c" * 64
        },
        predecessor_activation_terminal={
            "remote_materialization_transport_terminal_id": "d" * 64
        },
        preactivation_resource_result={
            "preactivation_resource_result_id": "e" * 64,
            "observed_python": {"python_version": [3, 12, 3]},
            "cgroup_memory_ancestry": [{"cgroup_path": "/"}],
            "memory_total_bytes": 1024,
            "memory_available_bytes": 512,
            "all_resource_gates_passed": True,
            "read_only_observation_completed": True,
            "remote_mutation_performed": False,
        },
        source_manifest={
            "source_commit": "f" * 40,
            "source_tree": "1" * 40,
            "source_manifest_id": "2" * 64,
        },
        transport_manifest={"transport_manifest_id": "3" * 64},
        local_materialization_attempt={
            "local_materialization_attempt_id": "4" * 64
        },
        remote_materialization_attempt={
            "remote_materialization_attempt_id": "5" * 64
        },
        materialization_terminal={"materialization_terminal_id": "6" * 64},
    )

    assert projected["activation_successor_final_evidence_index_id"] == HEX[
        native.SUCCESSOR_FINAL_FILE
    ]
    assert projected["non_authoritative_compatibility_artifact_id"] == HEX[
        native.LEGACY_CORE_ANCHOR_FILE
    ]
    assert projected["legacy_activation_final_evidence_index_claimed"] is False
    assert projected["legacy_snapshot_or_final_synthesized"] is False
    assert projected["activation_effect_replay_authorized"] is False
    assert "materialization_activation_final_evidence_index_id" not in projected
    assert "production_activation_core_id" not in projected


def test_historical_successor_sources_bind_declared_commit_without_head(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    commit = "1" * 40
    tree = "2" * 40
    raws = {
        relative: (relative + "\n").encode("utf-8")
        for relative in native.SUCCESSOR_CONTROLLER_TCB_PATHS
    }
    facts = []
    oid_to_raw: dict[str, bytes] = {}
    rows = []
    for relative in sorted(raws):
        raw = raws[relative]
        oid = hashlib.sha1(  # noqa: S324 - exact Git blob identity
            b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
        ).hexdigest()
        oid_to_raw[oid] = raw
        facts.append(
            {
                "relative_path": relative,
                "git_mode": "100644",
                "git_object_type": "blob",
                "git_blob_oid": oid,
                "byte_count": len(raw),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
        )
        rows.append((f"100644 blob {oid}\t{relative}").encode("utf-8"))
    calls: list[tuple[str, ...]] = []

    def run(*arguments: str) -> bytes:
        calls.append(arguments)
        assert not any("HEAD" in argument for argument in arguments)
        if arguments == ("--version",):
            return b"git version test\n"
        if arguments[-2:] == ("--verify", commit + "^{commit}"):
            return (commit + "\n").encode("ascii")
        if arguments[-2:] == ("--verify", commit + "^{tree}"):
            return (tree + "\n").encode("ascii")
        if "ls-tree" in arguments:
            return b"\0".join(rows) + b"\0"
        if "cat-file" in arguments:
            return oid_to_raw[arguments[-1]]
        raise AssertionError(arguments)

    monkeypatch.setattr(
        native,
        "_frozen_git_primitives",
        lambda: {
            "_run_fixed_git_v42r1": run,
            "GIT_VERSION_STDOUT": b"git version test\n",
        },
    )
    git_tree, observed = native._historical_successor_sources(  # noqa: SLF001
        {"source_commit": commit, "source_tree": tree, "source_facts": facts}
    )
    assert observed == raws
    assert set(git_tree) == native.SUCCESSOR_CONTROLLER_TCB_PATHS
    assert calls[0] == ("--version",)


def test_native_verifier_has_no_legacy_core_builder_or_effect_entry() -> None:
    source = Path(native.__file__).read_text(encoding="utf-8")
    assert "build_production_activation_core_v42r1(" not in source
    assert "verify_production_activation_core_v42r1(" not in source
    assert "execute_prepare_once_v42r1(" not in source
    assert "execute_launch_admission_once_v42r1(" not in source
    assert "def main(" not in source


def test_native_projection_rejects_missing_native_final() -> None:
    verified = _verified_successor()
    incomplete_ids = dict(verified.ids)
    del incomplete_ids[native.SUCCESSOR_FINAL_FILE]
    incomplete = native.VerifiedSuccessorDocumentsV42r2(
        documents=verified.documents,
        raws=verified.raws,
        ids=incomplete_ids,
        final=verified.final,
        legacy_core_anchor=verified.legacy_core_anchor,
    )
    with pytest.raises(KeyError):
        native.build_native_activation_inputs_v42r3(
            verified_successor=incomplete,
            materialization_activation_plan={
                "materialization_activation_plan_id": "a" * 64
            },
            predecessor_snapshot_tail_id="b" * 64,
            predecessor_classification={
                "materialization_activation_classification_id": "c" * 64
            },
            predecessor_activation_terminal={
                "remote_materialization_transport_terminal_id": "d" * 64
            },
            preactivation_resource_result={
                "preactivation_resource_result_id": "e" * 64,
                "observed_python": {"python_version": [3, 12, 3]},
                "cgroup_memory_ancestry": [{"cgroup_path": "/"}],
                "memory_total_bytes": 1024,
                "memory_available_bytes": 512,
                "all_resource_gates_passed": True,
                "read_only_observation_completed": True,
                "remote_mutation_performed": False,
            },
            source_manifest={
                "source_commit": "f" * 40,
                "source_tree": "1" * 40,
                "source_manifest_id": "2" * 64,
            },
            transport_manifest={"transport_manifest_id": "3" * 64},
            local_materialization_attempt={
                "local_materialization_attempt_id": "4" * 64
            },
            remote_materialization_attempt={
                "remote_materialization_attempt_id": "5" * 64
            },
            materialization_terminal={
                "materialization_terminal_id": "6" * 64
            },
        )
