from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp.science.execution_io_v1 import (
    ScienceExecutionIOV1Error,
    bound_clean_source_commit_v1,
    require_path_outside_repository_v1,
    write_exclusive_bytes_v1,
)
from acfqp.science.latent_resource_protocol_v1 import (
    LatentResourceProtocolV1Error,
    build_ratified_confirmatory_protocol_v1,
)
from acfqp.science.matched_double_dqn_2048_v1 import (
    CONFIRMATORY_RESULT_SCHEMA_V1,
)
from acfqp.science.statistics_gate_v1 import (
    CONFIRMATORY_RESULT_SCHEMA_V1 as GATE_CONFIRMATORY_RESULT_SCHEMA_V1,
)


REPOSITORY = Path(__file__).resolve().parents[1]


def _load_script(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, REPOSITORY / relative_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"cannot load {relative_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_source_binding_rejects_dirty_checkout(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    subprocess.run(["git", "init", "-q", str(repository)], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.email", "science@test.invalid"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repository), "config", "user.name", "Science Test"],
        check=True,
    )
    (repository / "tracked.txt").write_text("frozen\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repository), "add", "tracked.txt"], check=True)
    subprocess.run(
        ["git", "-C", str(repository), "commit", "-q", "-m", "freeze"],
        check=True,
    )

    source_commit = bound_clean_source_commit_v1(repository)
    assert len(source_commit) == 40
    (repository / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    with pytest.raises(ScienceExecutionIOV1Error, match="not clean"):
        bound_clean_source_commit_v1(repository)


def test_external_path_and_exclusive_output_contract(tmp_path: Path) -> None:
    repository = tmp_path / "source"
    repository.mkdir()
    with pytest.raises(ScienceExecutionIOV1Error, match="outside"):
        require_path_outside_repository_v1(
            repository=repository,
            path=repository / "artifacts" / "result.json",
            label="result",
        )

    output = require_path_outside_repository_v1(
        repository=repository,
        path=tmp_path / "results" / "result.json",
        label="result",
    )
    write_exclusive_bytes_v1(output, b"one")
    assert output.read_bytes() == b"one"
    with pytest.raises(FileExistsError):
        write_exclusive_bytes_v1(output, b"two")


def test_ratification_script_binds_source_and_writes_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ratifier = _load_script(
        "ratify_latent_resource_confirmatory_v1",
        "scripts/ratify_latent_resource_confirmatory_v1.py",
    )
    repository = tmp_path / "source"
    repository.mkdir()
    output = tmp_path / "ratified" / "confirmatory.json"
    monkeypatch.setattr(
        ratifier, "bound_clean_source_commit_v1", lambda _repository: "2" * 40
    )

    protocol = ratifier.ratify_confirmatory_protocol_file_v1(
        repository=repository, output=output
    )
    assert output.read_bytes() == canonical_json_bytes(protocol)
    assert protocol["source_commit"] == "2" * 40
    assert protocol["confirmatory_execution_authorized"] is True
    assert protocol["claim_boundary"]["official_execution_allowed"] is False
    assert protocol["claim_boundary"]["OFFICIAL_EXECUTION_GATE"] == "NOT_RUN"
    with pytest.raises(FileExistsError):
        ratifier.ratify_confirmatory_protocol_file_v1(
            repository=repository, output=output
        )


def test_confirmatory_runner_preflight_is_exact_and_cuda_only(tmp_path: Path) -> None:
    runner = _load_script(
        "run_matched_double_dqn_2048_confirmatory_v1",
        "scripts/run_matched_double_dqn_2048_confirmatory_v1.py",
    )
    protocol = build_ratified_confirmatory_protocol_v1("3" * 40)
    protocol_path = tmp_path / "protocol.json"
    protocol_path.write_text(json.dumps(protocol), encoding="utf-8")

    assert runner._load_protocol(protocol_path) == protocol
    runner._validate_execution_request(
        protocol=protocol,
        source_commit="3" * 40,
        arm="RESOURCE_STATE_ONLY_DROP_ANCHOR",
        seed=730101,
        device="cuda:0",
    )
    with pytest.raises(LatentResourceProtocolV1Error, match="source commit"):
        runner._validate_execution_request(
            protocol=protocol,
            source_commit="4" * 40,
            arm="RAW_BOARD",
            seed=730101,
            device="cuda:0",
        )
    with pytest.raises(LatentResourceProtocolV1Error, match="seed-arm"):
        runner._validate_execution_request(
            protocol=protocol,
            source_commit="3" * 40,
            arm="RESOURCE_STATE_ONLY_DROP_ANCHOR",
            seed=99,
            device="cuda:0",
        )
    changed_budget = json.loads(json.dumps(protocol))
    changed_budget["training"]["environment_steps_per_seed_arm"] = 499_999
    with pytest.raises(LatentResourceProtocolV1Error, match="budget"):
        runner._validate_execution_request(
            protocol=changed_budget,
            source_commit="3" * 40,
            arm="RAW_BOARD",
            seed=730101,
            device="cuda:0",
        )
    with pytest.raises(LatentResourceProtocolV1Error, match="CUDA"):
        runner._validate_execution_request(
            protocol=protocol,
            source_commit="3" * 40,
            arm="RAW_BOARD",
            seed=730101,
            device="cpu",
        )


def test_runtime_and_statistics_gate_share_confirmatory_schema() -> None:
    assert CONFIRMATORY_RESULT_SCHEMA_V1 == GATE_CONFIRMATORY_RESULT_SCHEMA_V1
