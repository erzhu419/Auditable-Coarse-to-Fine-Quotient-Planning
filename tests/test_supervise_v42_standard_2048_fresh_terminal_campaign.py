import ast
from pathlib import Path
import subprocess
import sys
import tempfile

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from scripts import supervise_v42_standard_2048_fresh_terminal_campaign as supervisor


def test_v42_supervisor_cli_has_no_board_seed_or_output_override() -> None:
    parsed = supervisor._parser().parse_args(["--formal-supervisor"])  # noqa: SLF001
    assert parsed.formal_supervisor is True
    with pytest.raises(SystemExit):
        supervisor._parser().parse_args(  # noqa: SLF001
            ["--formal-supervisor", "--output-dir", "/tmp/alternate"]
        )
    source = Path(supervisor.__file__).read_text(encoding="utf-8")
    assert "pre.EPISODE_SEEDS" not in source
    assert "select_seeded_outcome_v1" not in source
    assert "_issue_formal_execution_authority_v42" in source
    tree = ast.parse(source)
    top_level_imports = [
        node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    rendered = ast.unparse(ast.Module(body=top_level_imports, type_ignores=[]))
    assert "fresh_terminal_campaign_v42" not in rendered
    assert "fresh_terminal_independent_verifier_v42" not in rendered


def test_v42_producer_and_verifier_commands_are_fresh_isolated_python() -> None:
    producer = supervisor._isolated_command(  # noqa: SLF001
        "--producer-worker", "--authorization-fd", 17
    )
    verifier = supervisor._isolated_command(  # noqa: SLF001
        "--verifier-worker", "--campaign-fd", 19
    )
    assert producer[:5] == (
        sys.executable,
        "-I",
        "-S",
        "-B",
        str(Path(supervisor.__file__).resolve()),
    )
    assert verifier[:5] == producer[:5]
    assert producer[5:] == ("--producer-worker", "--authorization-fd", "17")
    assert verifier[5:] == ("--verifier-worker", "--campaign-fd", "19")


def test_v42_worker_start_is_o_excl_and_non_outcome() -> None:
    receipt = {
        "prepare_receipt_id": "1" * 64,
        "source_commit": "2" * 40,
        "source_tree": "3" * 40,
        "source_manifest_id": "4" * 64,
    }
    attempt = {"runner_attempt_id": "5" * 64}
    document = supervisor._worker_start_document(receipt, attempt)  # noqa: SLF001
    assert document["outcome_fields_present"] is False
    assert document["same_identity_worker_restart_forbidden"] is True
    assert document["producer_process_isolated"] is True
    assert document["verifier_process_isolated"] is True
    assert document["isolated_python_flags"] == ["-I", "-S", "-B"]
    raw = canonical_json_bytes(document)
    with tempfile.TemporaryDirectory(prefix="acfqp-v42-worker-", dir="/tmp") as root:
        path = Path(root) / "FIXTURE_WORKER_START.json"
        supervisor._write_worker_start_once(path, raw)  # noqa: SLF001
        with pytest.raises(FileExistsError):
            supervisor._write_worker_start_once(path, raw)  # noqa: SLF001


def test_v42_child_stdout_requires_exactly_one_trailing_newline() -> None:
    good = subprocess.CompletedProcess(
        args=("fixture",), returncode=0, stdout=b"{}\n", stderr=b""
    )
    assert supervisor._one_canonical_stdout(good, "fixture") == b"{}"  # noqa: SLF001
    for attacked in (b"{}", b"{}\n\n", b"{}\ntrailing"):
        completed = subprocess.CompletedProcess(
            args=("fixture",), returncode=0, stdout=attacked, stderr=b""
        )
        with pytest.raises(supervisor.V42SupervisedWorkerError):
            supervisor._one_canonical_stdout(completed, "fixture")  # noqa: SLF001
