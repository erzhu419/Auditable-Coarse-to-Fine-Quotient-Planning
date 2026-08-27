from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace

import pytest

from acfqp import construction_k7_standard_2048_execution_authority_v42 as authority
from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v42_standard_2048_fresh_terminal_campaign as runner


@pytest.fixture()
def linux_tmp_path() -> Path:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-journal-", dir="/tmp") as root:
        yield Path(root)


def _fixture_receipt_attempt() -> tuple[dict, dict]:
    receipt = {
        "prepare_receipt_id": "1" * 64,
        "source_commit": "2" * 40,
        "source_tree": "3" * 40,
        "source_manifest_id": "4" * 64,
    }
    attempt = {"runner_attempt_id": "5" * 64}
    return receipt, attempt


def test_v42_cli_has_only_prepare_or_launch_and_no_output_directory() -> None:
    assert runner._parser().parse_args(["--prepare"]).prepare is True  # noqa: SLF001
    assert runner._parser().parse_args(["--launch"]).launch is True  # noqa: SLF001
    with pytest.raises(SystemExit):
        runner._parser().parse_args(["--launch", "--output-dir", "/tmp/other"])  # noqa: SLF001
    assert authority.AUTHORITY_ROOT_RELATIVE != authority.EVIDENCE_ROOT_RELATIVE
    assert authority.FORMAL_IDENTITY.endswith("ORDINAL_1")


def test_v42_fixed_root_is_globally_exclusive(tmp_path: Path) -> None:
    root = tmp_path / "fixed-v42-identity"
    runner._create_one_shot_root(root)  # noqa: SLF001
    assert root.is_dir()
    with pytest.raises(runner.V42FormalRunnerError, match="rerun is forbidden"):
        runner._create_one_shot_root(root)  # noqa: SLF001


def test_v42_write_once_refuses_overwrite_and_classifies_exact() -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-runner-", dir="/tmp") as root:
        path = Path(root) / "FIXTURE_ATTEMPT.json"
        fact = runner._write_once(path, b"{}")  # noqa: SLF001
        assert fact["byte_count"] == 2
        assert authority.classify_artifact_bytes_v42(path, b"{}") == "EXACT"
        with pytest.raises(FileExistsError):
            runner._write_once(path, b"different")  # noqa: SLF001


def test_v42_partial_attempt_fault_is_typed_as_strict_prefix(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-partial-", dir="/tmp") as root:
        evidence = Path(root)
        expected = canonical_json_bytes({"fixture": "attempt", "ordinal": 1})
        real_write = runner.os.write
        calls = 0

        def partial_then_fail(descriptor: int, view: memoryview) -> int:
            nonlocal calls
            calls += 1
            if calls == 1:
                return real_write(descriptor, bytes(view[:5]))
            raise OSError("injected ATTEMPT fault")

        with monkeypatch.context() as scoped:
            scoped.setattr(runner.os, "write", partial_then_fail)
            with pytest.raises(OSError, match="injected ATTEMPT fault"):
                runner._write_once(  # noqa: SLF001
                    evidence / authority.ATTEMPT_NAME, expected
                )
        assert authority.classify_artifact_bytes_v42(
            evidence / authority.ATTEMPT_NAME, expected
        ) == "STRICT_PREFIX"
        receipt, attempt = _fixture_receipt_attempt()
        failure = runner._failure_document(  # noqa: SLF001
            stage="ATTEMPT_PUBLICATION",
            error=OSError("injected ATTEMPT fault"),
            receipt=receipt,
            attempt=attempt,
            evidence_root=evidence,
            expected_attempt_bytes=expected,
        )
        assert failure["artifact_states"][authority.ATTEMPT_NAME] == "STRICT_PREFIX"
        assert failure["scientific_success"] is False


@pytest.mark.parametrize(
    ("returncode", "expected"),
    [(-9, "WORKER_SIGNAL_SIGKILL_9"), (-15, "WORKER_SIGNAL_SIGTERM_15"), (137, "WORKER_OOM_OR_SIGKILL_STYLE_EXIT")],
)
def test_v42_worker_signal_and_oom_style_exits_are_typed(
    returncode: int, expected: str
) -> None:
    assert runner._worker_failure_classification(returncode) == expected  # noqa: SLF001
    completed = subprocess.CompletedProcess(
        args=("development-worker-fixture",),
        returncode=returncode,
        stdout=b"partial-result",
        stderr=b"killed",
    )
    with pytest.raises(runner.V42WorkerProcessError) as caught:
        runner._parse_worker_envelope(  # noqa: SLF001
            completed, receipt={}, attempt={}
        )
    assert caught.value.classification == expected


def test_v42_nested_producer_or_verifier_failure_classification_is_preserved() -> None:
    typed = canonical_json_bytes(
        {
            "schema": "acfqp.standard_2048_fresh_terminal_isolated_process_failure.v42",
            "failure_classification": "PRODUCER_SIGNAL_SIGKILL_9",
        }
    ) + b"\n"
    completed = subprocess.CompletedProcess(
        args=("isolated-supervisor-fixture",),
        returncode=70,
        stdout=b"",
        stderr=typed,
    )
    with pytest.raises(runner.V42WorkerProcessError) as caught:
        runner._parse_worker_envelope(completed, receipt={}, attempt={})  # noqa: SLF001
    assert caught.value.classification == "PRODUCER_SIGNAL_SIGKILL_9"


def test_v42_active_at_cap_is_nonzero_fail_closed_not_success() -> None:
    assert runner._scientific_exit_code(True) == 0  # noqa: SLF001
    assert runner._scientific_exit_code(False) == 2  # noqa: SLF001


@pytest.mark.parametrize("fault_kind", ["mkdir", "chmod", "fsync"])
def test_v42_prepare_root_creation_faults_close_in_fixed_parent_journal(
    monkeypatch: pytest.MonkeyPatch,
    linux_tmp_path: Path,
    fault_kind: str,
) -> None:
    tmp_path = linux_tmp_path
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    monkeypatch.setattr(
        runner.pre,
        "_freshness",
        lambda: {"history_freshness_manifest_id": "a" * 64},
    )
    frozen = SimpleNamespace(preregistration_id="b" * 64)
    monkeypatch.setattr(
        runner.pre,
        "freeze_standard_2048_fresh_terminal_preregistration_v42",
        lambda: frozen,
    )
    monkeypatch.setattr(
        runner.pre,
        "verify_standard_2048_fresh_terminal_preregistration_v42",
        lambda value: value,
    )
    monkeypatch.setattr(
        runner.authority,
        "build_prepare_receipt_v42",
        lambda *args, **kwargs: {
            "prepare_receipt_id": "c" * 64,
            "source_commit": "d" * 40,
        },
    )
    authority_root = runner.authority.fixed_authority_root_v42(tmp_path)
    if fault_kind == "mkdir":
        real_mkdir = runner.os.mkdir

        def faulting_mkdir(path: Path, mode: int = 0o777) -> None:
            if Path(path) == authority_root:
                raise OSError("injected authority-root mkdir fault")
            real_mkdir(path, mode)

        monkeypatch.setattr(runner.os, "mkdir", faulting_mkdir)
    elif fault_kind == "chmod":
        real_chmod = runner.os.chmod

        def faulting_chmod(path: Path, mode: int) -> None:
            if Path(path) == authority_root:
                raise OSError("injected authority-root chmod fault")
            real_chmod(path, mode)

        monkeypatch.setattr(runner.os, "chmod", faulting_chmod)
    else:
        real_fsync_directory = runner._fsync_directory  # noqa: SLF001

        def faulting_fsync_directory(path: Path) -> None:
            if Path(path) == authority_root:
                raise OSError("injected authority-root fsync fault")
            real_fsync_directory(path)

        monkeypatch.setattr(runner, "_fsync_directory", faulting_fsync_directory)

    with pytest.raises(OSError, match="injected authority-root"):
        runner._prepare()  # noqa: SLF001
    assert (tmp_path / runner.authority.PREPARE_ATTEMPT_JOURNAL_NAME).is_file()
    failure_path = tmp_path / runner.authority.PREPARE_FAILURE_JOURNAL_NAME
    assert failure_path.is_file()
    failure = runner.loads_canonical_json(failure_path.read_bytes())
    assert failure["formal_execution_performed"] is False
    assert failure["same_identity_prepare_retry_forbidden"] is True


def test_v42_launch_evidence_root_fault_closes_in_existing_parent_journal(
    monkeypatch: pytest.MonkeyPatch,
    linux_tmp_path: Path,
) -> None:
    tmp_path = linux_tmp_path
    monkeypatch.setattr(runner, "ROOT", tmp_path)
    authority_root = runner.authority.fixed_authority_root_v42(tmp_path)
    authority_root.mkdir(parents=True)
    (authority_root / runner.authority.PREPARE_RECEIPT_NAME).write_bytes(b"{}")
    receipt = {
        "prepare_receipt_id": "1" * 64,
        "fresh_terminal_preregistration_id": runner.pre.PREREGISTRATION_ID,
        "history_freshness_manifest_id": "2" * 64,
        "source_commit": "3" * 40,
        "source_tree": "4" * 40,
        "source_manifest_id": "5" * 64,
        "source_manifest": {},
    }
    monkeypatch.setattr(
        runner.pre,
        "_freshness",
        lambda: {"history_freshness_manifest_id": "2" * 64},
    )
    monkeypatch.setattr(
        runner.authority,
        "verify_prepare_receipt_v42",
        lambda *args, **kwargs: receipt,
    )
    monkeypatch.setattr(
        runner.authority,
        "verify_live_source_matches_manifest_v42",
        lambda *args, **kwargs: None,
    )
    evidence_root = runner.authority.fixed_evidence_root_v42(tmp_path)

    def fail_evidence_root(path: Path) -> None:
        assert path == evidence_root
        raise OSError("injected evidence-root creation fault")

    monkeypatch.setattr(runner, "_create_one_shot_root", fail_evidence_root)
    with pytest.raises(OSError, match="injected evidence-root"):
        runner._launch()  # noqa: SLF001
    assert (tmp_path / runner.authority.LAUNCH_ATTEMPT_JOURNAL_NAME).is_file()
    failure_path = tmp_path / runner.authority.LAUNCH_FAILURE_JOURNAL_NAME
    assert failure_path.is_file()
    failure = runner.loads_canonical_json(failure_path.read_bytes())
    assert failure["failure_stage"] == "EVIDENCE_ROOT_CREATION"
    assert failure["scientific_success"] is False


def test_v42_failure_text_and_worker_captures_are_bounded() -> None:
    receipt, attempt = _fixture_receipt_attempt()
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-bounds-", dir="/tmp") as root:
        failure = runner._failure_document(  # noqa: SLF001
            stage="FIXTURE",
            error=RuntimeError("x" * (runner.MAX_EXCEPTION_MESSAGE_BYTES * 2)),
            receipt=receipt,
            attempt=attempt,
            evidence_root=Path(root),
            expected_attempt_bytes=b"{}",
        )
    assert len(failure["failure_message"].encode("utf-8")) <= runner.MAX_EXCEPTION_MESSAGE_BYTES
    assert failure["worker_stdout"]["capture_was_bounded"] is True
