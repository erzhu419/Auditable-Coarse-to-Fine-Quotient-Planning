from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/launch_v180r12r2_ten_terminal_aggregation_prelaunch.py"
SPEC = importlib.util.spec_from_file_location("v180r12r2_prelaunch_launcher", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
launcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(launcher)


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def _write_0400(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    path.chmod(0o400)


def _fact(relative_path: str, raw: bytes) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "byte_count": len(raw),
        "sha256": hashlib.sha256(raw).hexdigest(),
    }


def _git_fact(relative_path: str, raw: bytes, blob: str) -> dict[str, object]:
    return {
        **_fact(relative_path, raw),
        "git_mode": "100644",
        "git_blob_id": blob,
    }


def _closure(facts: list[dict[str, object]]) -> dict[str, object]:
    return {
        "facts": facts,
        "file_count": len(facts),
        "total_byte_count": sum(int(row["byte_count"]) for row in facts),
        "facts_sha256": hashlib.sha256(_canonical(facts)).hexdigest(),
    }


def _materialized_repository(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[Path, str]:
    repository = tmp_path / "repository"
    repository.mkdir()
    prelaunch = repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH
    prelaunch.mkdir(parents=True)
    prelaunch.chmod(0o700)

    bootstrap_raw = b"# retained bootstrap\n"
    launcher_raw = SCRIPT.read_bytes()
    wrapper_raw = b"EXPECTED_AUTHORIZATION_ID = 'literal'\n"
    wrapper_normalized_raw = b"EXPECTED_AUTHORIZATION_ID = 0\n"
    wrapper_raw_fact = _fact(
        launcher.AUTHORIZATION_EVIDENCE_RELATIVE_PATH, wrapper_raw
    )
    wrapper_normalized_fact = {
        **_fact(
            launcher.AUTHORIZATION_EVIDENCE_RELATIVE_PATH,
            wrapper_normalized_raw,
        ),
        "binding_kind": launcher.NORMALIZED_WRAPPER_BINDING_KIND,
        "redacted_constant_names": list(
            launcher.WRAPPER_REDACTED_CONSTANT_NAMES
        ),
    }
    authorization_closure = _closure([wrapper_normalized_fact])
    third_party_closure = _closure(
        [
            {
                **_fact("packaging/__init__.py", b"# packaging\n"),
                "module": "packaging",
                "is_package": True,
                "source_root": "/bound/third-party",
            }
        ]
    )
    manifest = {
        "schema": "acfqp.v180r12r2_source_bound_launch_manifest.v1",
        "repository_root": str(repository),
        "c_pre_root": str(prelaunch),
        "manifest_relative_path": "launch_manifest.json",
        "c_pre_commit_id": "a" * 40,
        "bootstrap": _fact("bootstrap.py", bootstrap_raw),
        "runtime": {},
        "git": {},
        "authorization_source_closure_kind": "TEST_BOUND_CLOSURE",
        "authorization_self_module": "acfqp.test_authorization",
        "authorization_raw_source_modules": ["acfqp.test_wrapper"],
        "authorization_source_closure": authorization_closure,
        "source_modules": [
            {
                **wrapper_raw_fact,
                "module": "acfqp.test_wrapper",
                "is_package": False,
            }
        ],
        "third_party_source_closure": third_party_closure,
        "targets": {
            "production": _fact(
                "scripts/run_v180r12r2_ten_terminal_aggregation.py",
                b"# production\n",
            ),
            "verification": _fact(
                "scripts/verify_v180r12r2_ten_terminal_aggregation.py",
                b"# verification\n",
            ),
        },
        "working_tree_mutation_after_snapshot_in_scope": False,
    }
    manifest_raw = _canonical(manifest)
    _write_0400(repository / launcher.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw)
    _write_0400(repository / launcher.LAUNCHER_RELATIVE_PATH, launcher_raw)
    _write_0400(repository / launcher.MANIFEST_RELATIVE_PATH, manifest_raw)
    monkeypatch.setattr(
        launcher,
        "__file__",
        str(repository / launcher.LAUNCHER_RELATIVE_PATH),
    )
    monkeypatch.setattr(
        launcher.sys,
        "argv",
        [str(repository / launcher.LAUNCHER_RELATIVE_PATH)],
    )

    bootstrap_git_fact = _git_fact(
        launcher.SOURCE_BOOTSTRAP_RELATIVE_PATH, bootstrap_raw, "1" * 40
    )
    launcher_git_fact = _git_fact(
        launcher.SOURCE_LAUNCHER_RELATIVE_PATH, launcher_raw, "2" * 40
    )
    materializer_git_fact = _git_fact(
        launcher.SOURCE_MATERIALIZER_RELATIVE_PATH, b"# materializer\n", "3" * 40
    )
    external_root = {
        "schema": "acfqp.v180r12r2_prelaunch_external_root.v1",
        "materialization_rule_id": launcher.MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": launcher.SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "git_directory": str(repository / ".git"),
        "c_pre_commit_id": "a" * 40,
        "c_pre_tree_id": "4" * 40,
        "bootstrap_git_blob": bootstrap_git_fact,
        "launcher_git_blob": launcher_git_fact,
        "materializer_git_blob": materializer_git_fact,
        "third_party_source_roots": {
            "packaging": "/bound/third-party",
            "tomli": "/bound/third-party",
        },
        "created_before_v180r12r2_authorized_production_execution": True,
        "v180r12r2_outcome_bytes_accessed": False,
    }
    external_raw = _canonical(external_root)
    external_path = repository / launcher.EXTERNAL_ROOT_RELATIVE_PATH
    _write_0400(external_path, external_raw)

    payload = {
        "schema": launcher.MATERIALIZATION_TERMINAL_SCHEMA,
        "materialization_rule_id": launcher.MATERIALIZATION_RULE_ID,
        "source_closure_rule_id": launcher.SOURCE_CLOSURE_RULE_ID,
        "repository_root": str(repository),
        "external_root": {
            "absolute_path": str(external_path),
            "byte_count": len(external_raw),
            "sha256": hashlib.sha256(external_raw).hexdigest(),
            "immutable_mode": "0400",
        },
        "git_topology": {
            "c_pre_commit_id": "a" * 40,
            "c_pre_tree_id": "4" * 40,
            "empty_bridge_commit_id": "b" * 40,
            "empty_bridge_tree_id": "4" * 40,
            "literal_commit_id": "c" * 40,
            "literal_commit_tree_id": "5" * 40,
            "literal_wrapper_prior_blob_id": "6" * 40,
            "literal_wrapper_blob_id": "7" * 40,
        },
        "bootstrap_source_git_blob": bootstrap_git_fact,
        "materializer_source_git_blob": materializer_git_fact,
        "launcher_source_git_blob": launcher_git_fact,
        "retained_bootstrap": _fact(launcher.BOOTSTRAP_RELATIVE_PATH, bootstrap_raw),
        "retained_launcher": _fact(launcher.LAUNCHER_RELATIVE_PATH, launcher_raw),
        "launch_manifest": _fact(launcher.MANIFEST_RELATIVE_PATH, manifest_raw),
        "materialization_terminal_relative_path": (
            launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
        ),
        "materialization_failure_relative_path": (
            launcher.MATERIALIZATION_FAILURE_RELATIVE_PATH
        ),
        "authorization_source_closure_file_count": authorization_closure[
            "file_count"
        ],
        "authorization_source_closure_total_byte_count": authorization_closure[
            "total_byte_count"
        ],
        "authorization_source_closure_facts_sha256": authorization_closure[
            "facts_sha256"
        ],
        "third_party_source_closure_file_count": third_party_closure[
            "file_count"
        ],
        "third_party_source_closure_total_byte_count": third_party_closure[
            "total_byte_count"
        ],
        "third_party_source_closure_facts_sha256": third_party_closure[
            "facts_sha256"
        ],
        "normalized_wrapper_fact": wrapper_normalized_fact,
        "current_literal_wrapper_raw_observation": wrapper_raw_fact,
        "launch_manifest_digest_is_runtime_supplied_not_protocol_frozen": True,
        "launch_manifest_has_no_self_digest": True,
        "external_root_created_before_authorized_production_execution": True,
        "external_root_required_before_authorization_issuance": False,
        "materialization_terminal_written_last": True,
        "write_once_o_excl": True,
        "write_no_follow": True,
        "close_on_exec": True,
        "output_directory_mode": "0700",
        "output_file_mode": "0400",
        "file_and_directory_fsync_required": True,
        "same_materialization_identity_rerun_forbidden": True,
        "construction_only": True,
        "preauthorization_supervision": True,
        "campaign_actual_measurement": False,
        "scientific_occurrence_executed": False,
        "v180r12r2_outcome_bytes_accessed": False,
        "counter_records_issued": False,
        "work_vectors_issued": False,
        "comparison_vectors_issued": False,
        "COUNTER_COMPLETENESS_GATE": "NOT_RUN",
        "WORKLOAD_ECONOMICS_GATE": "NOT_RUN",
        "SCALAR_CALIBRATION_GATE": "NOT_RUN",
        "BREAK_EVEN_GATE": "NOT_RUN",
        "official_execution_allowed": False,
        "success": True,
    }
    terminal = {
        **payload,
        "materialization_terminal_id": hashlib.sha256(_canonical(payload)).hexdigest(),
    }
    terminal_raw = _canonical(terminal)
    _write_0400(
        repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH,
        terminal_raw,
    )
    return repository, hashlib.sha256(terminal_raw).hexdigest()


def test_rule_freezes_whole_child_cap_and_attempt_first() -> None:
    assert launcher.LAUNCH_RULE_ID == hashlib.sha256(
        _canonical(launcher.LAUNCH_RULE_DOCUMENT)
    ).hexdigest()
    assert launcher.LAUNCH_RULE_DOCUMENT["address_space_hard_cap_bytes"] == (
        16 * 1024 * 1024 * 1024
    )
    assert launcher.LAUNCH_RULE_DOCUMENT["attempt_lock_written_before_child_exec"]
    assert launcher.LAUNCH_RULE_DOCUMENT["campaign_actual_measurement"] is False


def test_preexec_applies_rlimit_before_exec(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[object] = []
    monkeypatch.setattr(launcher.os, "setsid", lambda: events.append("setsid"))
    monkeypatch.setattr(
        launcher.resource,
        "setrlimit",
        lambda kind, value: events.append((kind, value)),
    )
    launcher._child_preexec()
    assert events == [
        "setsid",
        (
            launcher.resource.RLIMIT_AS,
            (
                launcher.ADDRESS_SPACE_HARD_CAP_BYTES,
                launcher.ADDRESS_SPACE_HARD_CAP_BYTES,
            ),
        ),
    ]


def test_production_attempt_precedes_child_and_success_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(argv: list[str], environment: dict[str, str]):
        attempt = repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH
        assert attempt.is_file()
        assert environment == {
            launcher.MANIFEST_SHA256_ENV: hashlib.sha256(
                (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
            ).hexdigest(),
            "LC_CTYPE": "C.UTF-8",
        }
        output = repository / launcher.OUTPUT_ROOT_RELATIVE_PATH
        output.mkdir()
        (output / "TERMINAL.json").write_bytes(b"{}")
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    receipt = launcher.launch_prelaunch_target_v180r12r2(
        "production", repository, digest
    )
    assert receipt["schema"] == launcher.LAUNCH_RECEIPT_SCHEMA
    assert receipt["success"] is True
    assert (repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH).is_file()
    assert (repository / launcher.PRODUCTION_RECEIPT_RELATIVE_PATH).is_file()
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
    )
    with pytest.raises(launcher.V180r12r2PrelaunchLaunchReplayForbidden):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )


def test_bootstrap_failure_preserves_attempt_and_typed_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fail_before_runner(_argv: list[str], _environment: dict[str, str]):
        assert (repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH).is_file()
        raise ValueError("bootstrap primary")

    monkeypatch.setattr(launcher, "_run_child", fail_before_runner)
    with pytest.raises(ValueError, match="bootstrap primary"):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    failure_path = repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert failure["schema"] == launcher.LAUNCH_FAILURE_SCHEMA
    assert failure["failure_type"] == "ValueError"
    assert failure["failure_message"] == "bootstrap primary"
    assert failure["attempt_lock_preserved"] is True
    assert failure["same_target_identity_rerun_forbidden"] is True


def test_verification_requires_successful_production_and_writes_own_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    prelaunch = repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH
    materialization, materialization_raw = launcher._load_materialization(
        repository, digest
    )
    attempt, attempt_raw = launcher._attempt_document(
        target="production",
        repository_root=repository,
        materialization=materialization,
        materialization_raw=materialization_raw,
        manifest_sha256=hashlib.sha256(
            (repository / launcher.MANIFEST_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
        child_argv=[
            *launcher.ISOLATED_ARGV_PREFIX,
            str(repository / launcher.BOOTSTRAP_RELATIVE_PATH),
            "production",
            str(repository),
            str(repository / launcher.PRELAUNCH_ROOT_RELATIVE_PATH),
            str(repository / launcher.MANIFEST_RELATIVE_PATH),
        ],
    )
    _write_0400(prelaunch / "PRODUCTION_LAUNCH_ATTEMPT.json", attempt_raw)
    output = repository / launcher.OUTPUT_ROOT_RELATIVE_PATH
    output.mkdir()
    (output / "TERMINAL.json").write_bytes(b"{}")
    prior_progress = launcher._progress_observations(
        launcher._state_paths(repository, "production")
    )
    empty = launcher._StreamObservation().document()
    prior_receipt, prior_receipt_raw = launcher._terminal_document(
        schema=launcher.LAUNCH_RECEIPT_SCHEMA,
        id_key="launch_receipt_id",
        target="production",
        attempt=attempt,
        return_code=0,
        timed_out=False,
        stdout=empty,
        stderr=empty,
        progress=prior_progress,
        error=None,
    )
    assert prior_receipt["success"] is True
    _write_0400(prelaunch / "PRODUCTION_LAUNCH_RECEIPT.json", prior_receipt_raw)

    def fake_verify(_argv: list[str], _environment: dict[str, str]):
        (repository / launcher.VERIFICATION_RELATIVE_PATH).write_bytes(b"{}")
        (repository / launcher.RETAINED_REPLAY_RELATIVE_PATH).write_bytes(b"{}")
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_verify)
    receipt = launcher.launch_prelaunch_target_v180r12r2(
        "verification", repository, digest
    )
    assert receipt["target"] == "verification"
    assert receipt["success"] is True
    assert (repository / launcher.VERIFICATION_ATTEMPT_RELATIVE_PATH).is_file()
    assert (repository / launcher.VERIFICATION_RECEIPT_RELATIVE_PATH).is_file()


def test_child_stream_cap_is_constant_memory() -> None:
    observation = launcher._StreamObservation()
    observation.add(b"x" * 8192)
    document = observation.document()
    assert document["byte_count"] == 8192
    assert len(bytes.fromhex(document["retained_prefix_hex"])) == 4096
    assert document["retained_prefix_truncated"] is True


def test_partial_attempt_write_still_freezes_typed_launch_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def fail_after_attempt_create(path: Path, raw: bytes) -> None:
        if path == repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH:
            _write_0400(path, raw[:17])
            raise OSError("injected partial attempt fsync failure")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_write_once", fail_after_attempt_create)
    with pytest.raises(OSError, match="partial attempt"):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    failure_path = repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
    failure = json.loads(failure_path.read_text(encoding="utf-8"))
    assert failure["failure_type"] == "OSError"
    assert failure["progress_observations"]["attempt"] == {
        "presence": "REGULAR_FILE",
        "mode": 0o400,
        "byte_count": 17,
        "sha256": hashlib.sha256(
            (repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH).read_bytes()
        ).hexdigest(),
    }


def test_concurrent_attempt_lock_loser_does_not_poison_winner_with_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def lose_attempt_race(path: Path, raw: bytes) -> None:
        if path == repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH:
            original_write_once(path, raw)
            raise FileExistsError("concurrent attempt owner")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_write_once", lose_attempt_race)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchReplayForbidden,
        match="concurrently",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    assert (repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH).is_file()
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
    )
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_RECEIPT_RELATIVE_PATH
    )


def test_launch_failure_coexistence_forbids_success_receipt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(_argv: list[str], _environment: dict[str, str]):
        output = repository / launcher.OUTPUT_ROOT_RELATIVE_PATH
        output.mkdir()
        (output / "TERMINAL.json").write_bytes(b"{}")
        _write_0400(
            repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH,
            b"{}",
        )
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_RECEIPT_RELATIVE_PATH
    )


def test_production_child_leaving_runtime_cas_cannot_receive_success(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_run(_argv: list[str], _environment: dict[str, str]):
        output = repository / launcher.OUTPUT_ROOT_RELATIVE_PATH
        output.mkdir()
        (output / "TERMINAL.json").write_bytes(b"{}")
        (repository / launcher.RUNTIME_CAS_ROOT_RELATIVE_PATH).mkdir()
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_run)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="durable success",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_RECEIPT_RELATIVE_PATH
    )
    assert os.path.lexists(
        repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH
    )


def test_launch_failure_write_secondary_never_replaces_primary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    original_write_once = launcher._write_once

    def fail_child(_argv: list[str], _environment: dict[str, str]):
        raise ValueError("primary bootstrap failure")

    def fail_failure_write(path: Path, raw: bytes) -> None:
        if path == repository / launcher.PRODUCTION_LAUNCH_FAILURE_RELATIVE_PATH:
            raise OSError("secondary failure write")
        original_write_once(path, raw)

    monkeypatch.setattr(launcher, "_run_child", fail_child)
    monkeypatch.setattr(launcher, "_write_once", fail_failure_write)
    with pytest.raises(ValueError, match="primary bootstrap") as captured:
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    assert isinstance(captured.value.__cause__, OSError)
    assert "secondary failure write" in str(captured.value.__cause__)


def test_resigned_foreign_production_receipt_is_rejected_before_verification(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)

    def fake_production(_argv: list[str], _environment: dict[str, str]):
        output = repository / launcher.OUTPUT_ROOT_RELATIVE_PATH
        output.mkdir()
        (output / "TERMINAL.json").write_bytes(b"{}")
        empty = launcher._StreamObservation().document()
        return 0, False, empty, empty

    monkeypatch.setattr(launcher, "_run_child", fake_production)
    launcher.launch_prelaunch_target_v180r12r2("production", repository, digest)
    receipt_path = repository / launcher.PRODUCTION_RECEIPT_RELATIVE_PATH
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt.pop("launch_receipt_id")
    receipt["foreign_resigned_field"] = True
    receipt["launch_receipt_id"] = hashlib.sha256(_canonical(receipt)).hexdigest()
    receipt_path.chmod(0o600)
    receipt_path.write_bytes(_canonical(receipt))
    receipt_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="schema changed",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "verification", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.VERIFICATION_ATTEMPT_RELATIVE_PATH
    )


def test_materialization_terminal_resign_cannot_weaken_write_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    terminal_path = repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    terminal.pop("materialization_terminal_id")
    terminal["file_and_directory_fsync_required"] = False
    terminal["materialization_terminal_id"] = hashlib.sha256(
        _canonical(terminal)
    ).hexdigest()
    terminal_raw = _canonical(terminal)
    terminal_path.chmod(0o600)
    terminal_path.write_bytes(terminal_raw)
    terminal_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="boundary changed",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production",
            repository,
            hashlib.sha256(terminal_raw).hexdigest(),
        )


def test_resigned_retained_bootstrap_cannot_disconnect_c_pre_git_blob(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, _digest = _materialized_repository(tmp_path, monkeypatch)
    terminal_path = repository / launcher.MATERIALIZATION_TERMINAL_RELATIVE_PATH
    terminal = json.loads(terminal_path.read_text(encoding="utf-8"))
    terminal.pop("materialization_terminal_id")
    terminal["retained_bootstrap"]["sha256"] = "f" * 64
    terminal["materialization_terminal_id"] = hashlib.sha256(
        _canonical(terminal)
    ).hexdigest()
    terminal_raw = _canonical(terminal)
    terminal_path.chmod(0o600)
    terminal_path.write_bytes(terminal_raw)
    terminal_path.chmod(0o400)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="differs from its C_pre Git blob",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production",
            repository,
            hashlib.sha256(terminal_raw).hexdigest(),
        )


def test_materialization_failure_sibling_forbids_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository, digest = _materialized_repository(tmp_path, monkeypatch)
    failure = repository / launcher.MATERIALIZATION_FAILURE_RELATIVE_PATH
    _write_0400(failure, b"{}")
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchReplayForbidden,
        match="materialization failure",
    ):
        launcher.launch_prelaunch_target_v180r12r2(
            "production", repository, digest
        )
    assert not os.path.lexists(
        repository / launcher.PRODUCTION_ATTEMPT_RELATIVE_PATH
    )


def test_process_group_is_terminated_even_after_leader_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[tuple[int, int]] = []

    def fake_killpg(pid: int, sig: int) -> None:
        events.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError

    monkeypatch.setattr(launcher.os, "killpg", fake_killpg)
    launcher._terminate_process_group(SimpleNamespace(pid=811, poll=lambda: 0))
    assert events == [(811, launcher.signal.SIGTERM), (811, 0)]


def test_startup_rejects_wrong_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repository = tmp_path / "repository"
    repository.mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    retained = repository / launcher.LAUNCHER_RELATIVE_PATH
    retained.parent.mkdir(parents=True)
    retained.write_bytes(SCRIPT.read_bytes())
    monkeypatch.setattr(launcher, "__file__", str(retained))
    monkeypatch.setattr(launcher.sys, "executable", launcher.PYTHON_EXECUTABLE)
    monkeypatch.setattr(launcher.sys, "pycache_prefix", launcher.PYCACHE_PREFIX)
    monkeypatch.setattr(launcher.sys, "dont_write_bytecode", True)
    monkeypatch.setattr(
        launcher.sys,
        "flags",
        SimpleNamespace(
            isolated=1,
            no_site=1,
            no_user_site=1,
            ignore_environment=1,
            dont_write_bytecode=1,
        ),
    )
    expected = [
        *launcher.ISOLATED_ARGV_PREFIX,
        str(retained),
        "production",
        str(repository),
    ]
    monkeypatch.setattr(launcher.sys, "orig_argv", expected)
    monkeypatch.setattr(
        launcher.sys,
        "argv",
        expected[len(launcher.ISOLATED_ARGV_PREFIX) :],
    )
    monkeypatch.setattr(
        launcher.os,
        "environ",
        {
            launcher.MATERIALIZATION_TERMINAL_SHA256_ENV: "a" * 64,
            "LC_CTYPE": "C.UTF-8",
        },
    )
    monkeypatch.chdir(elsewhere)
    with pytest.raises(
        launcher.V180r12r2PrelaunchLaunchError,
        match="working directory",
    ):
        launcher._require_launcher_startup("production", repository)
