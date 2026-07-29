from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from scripts import run_v072_registered_campaign as cli


def _id(character: str) -> str:
    return character * 64


def _install_authority_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    root: Path,
    calls: list[str],
) -> tuple[Any, Any, Any]:
    source_replay = SimpleNamespace(replay_id=_id("7"))
    manifest = SimpleNamespace(
        manifest_id=_id("b"),
        source_reconstruction_replay=source_replay,
    )
    final = SimpleNamespace(
        manifest=manifest,
        manifest_id=manifest.manifest_id,
        final_preregistration_id=_id("c"),
    )
    claim = SimpleNamespace(
        claim_id=_id("d"),
        source_reconstruction_recipe_id=_id("a"),
        manifest_id=manifest.manifest_id,
        final_preregistration_id=final.final_preregistration_id,
    )
    attestation = SimpleNamespace(verification_id=_id("f"))
    anchor = SimpleNamespace(
        claim=claim,
        anchor_id=_id("e"),
        independent_semantic_attestation=attestation,
    )
    chain = SimpleNamespace(
        chain_id=_id("1"),
        manifest=manifest,
        remote_main_anchor=anchor,
    )

    def finalize(repository_root: Path) -> Any:
        assert repository_root == root
        calls.append("FINALIZE")
        return final

    def derive(repository_root: Path) -> Any:
        assert repository_root == root
        calls.append("DERIVE_ANCHOR_CLAIM")
        return claim

    def mint(*, repository_root: Path) -> Any:
        assert repository_root == root
        calls.append("MINT_ANCHOR")
        return anchor

    def construct_chain(**kwargs: Any) -> Any:
        assert kwargs == {
            "manifest": manifest,
            "final_preregistration": final,
            "remote_main_anchor": anchor,
            "remote_main_anchor_attestation": attestation,
            "repository_root": str(root),
        }
        calls.append("CONSTRUCT_CHAIN")
        return chain

    def verify_chain(value: Any) -> tuple[str, str, str, str, str]:
        assert value is chain
        calls.append("VERIFY_CHAIN")
        return (
            _id("a"),
            manifest.manifest_id,
            final.final_preregistration_id,
            anchor.anchor_id,
            attestation.verification_id,
        )

    monkeypatch.setattr(cli, "_repository_root_v1", lambda: root)
    monkeypatch.setattr(
        cli.final_authority,
        "finalize_v072_final_preregistration_v1",
        finalize,
    )
    monkeypatch.setattr(
        cli.final_authority,
        "derive_v072_remote_main_anchor_claim_v1",
        derive,
    )
    monkeypatch.setattr(
        cli.final_authority,
        "mint_v072_remote_main_anchor_v1",
        mint,
    )
    monkeypatch.setattr(
        cli.consumer,
        "RegisteredCampaignAuthorityChainV1",
        construct_chain,
    )
    monkeypatch.setattr(
        cli.consumer,
        "verify_registered_campaign_authority_chain_v1",
        verify_chain,
    )
    return chain, claim, anchor


class _JournalHarness:
    def __init__(
        self,
        root: Path,
        chain: Any,
        plan: Any,
        calls: list[str],
    ) -> None:
        self.root = root
        self.chain = chain
        self.plan = plan
        self.calls = calls
        self.terminal = False
        self.attempt_directory = root / "artifacts" / "journal-harness"
        self.identity = SimpleNamespace(attempt_id=_id("journal-identity"))
        self.caught_error: BaseException | None = None
        self.caught_phase: str | None = None

    def bind_source_replay(self, replay: Any) -> None:
        assert replay is self.chain.manifest.source_reconstruction_replay
        self.calls.append("JOURNAL_BIND_SOURCE")

    def commit_computation_result(self, execution_result: Any) -> None:
        assert execution_result is not None
        self.calls.append("JOURNAL_COMPUTATION")

    def commit_output_published(
        self,
        *,
        output_path: Path,
        execution_result_id: str,
    ) -> None:
        assert output_path.is_file()
        assert execution_result_id == _id("5")
        self.calls.append("JOURNAL_OUTPUT_PUBLISHED")
        self.terminal = True

    def commit_caught_failure(
        self,
        error: BaseException,
        *,
        runner_phase: str,
    ) -> None:
        self.caught_error = error
        self.caught_phase = runner_phase
        self.calls.append("JOURNAL_CAUGHT_FAILURE")
        self.terminal = True


def _install_journal_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    *,
    root: Path,
    chain: Any,
    calls: list[str],
    output_repository_path: str = (
        "artifacts/v072_registered_campaign_result_v1.json"
    ),
) -> _JournalHarness:
    plan = SimpleNamespace(plan_id=_id("8"))
    writer = _JournalHarness(root, chain, plan, calls)

    def prepare(authority_chain: Any) -> Any:
        assert authority_chain is chain
        calls.append("PREPARE_EXECUTION_PLAN")
        return plan

    def open_journal(**kwargs: Any) -> _JournalHarness:
        assert kwargs == {
            "repository_root": root,
            "authority_chain": chain,
            "execution_plan": plan,
            "output_repository_path": output_repository_path,
        }
        calls.append("OPEN_ATTEMPT_JOURNAL")
        return writer

    def verify(
        path: Path,
        *,
        expected_identity: Any,
    ) -> Any:
        assert path == writer.attempt_directory
        assert expected_identity is writer.identity
        calls.append("VERIFY_ATTEMPT_JOURNAL")
        return SimpleNamespace(
            attempt_id=_id("9"),
            closure=SimpleNamespace(value="OUTPUT_PUBLISHED"),
        )

    def close(value: Any) -> None:
        assert value is writer
        calls.append("CLOSE_ATTEMPT_JOURNAL")

    monkeypatch.setattr(
        cli.consumer,
        "prepare_registered_campaign_execution_plan_v1",
        prepare,
    )
    monkeypatch.setattr(
        cli.attempt_journal,
        "open_registered_campaign_attempt_journal_v1",
        open_journal,
    )
    monkeypatch.setattr(
        cli.attempt_journal,
        "verify_attempt_journal_v1",
        verify,
    )
    monkeypatch.setattr(
        cli.attempt_journal,
        "close_active_attempt_journal_v1",
        close,
    )
    return writer


def test_cli_accepts_no_evidence_status_count_seed_or_git_identity() -> None:
    assert tuple(inspect.signature(cli.main).parameters) == ("argv",)
    assert cli.DEFAULT_OUTPUT_RELATIVE_PATH == Path(
        "artifacts/v072_registered_campaign_result_v1.json"
    )
    for arguments in (
        ("--evidence", "foreign.json"),
        ("--status", "PASS"),
        ("--count", "15"),
        ("--seed", "7"),
        ("--commit-id", _id("2")),
        ("--tree-id", _id("3")),
        ("--repository-root", "/tmp/foreign"),
    ):
        with pytest.raises(SystemExit) as captured:
            cli.main(list(arguments))
        assert captured.value.code == 2


def test_campaign_writes_exact_full_canonical_document_once(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = (tmp_path / "repo").resolve()
    output_parent = root / "artifacts"
    output_parent.mkdir(parents=True)
    output = output_parent / "v072_registered_campaign_result_v1.json"
    calls: list[str] = []
    chain, _, _ = _install_authority_boundaries(
        monkeypatch,
        root,
        calls,
    )
    _install_journal_boundaries(
        monkeypatch,
        root=root,
        chain=chain,
        calls=calls,
    )
    full_document = {
        "schema": "acfqp.v072_registered_campaign_execution_result.v1",
        "complete_bundle": {
            "route_results": [{"route_id": _id("4")}],
            "reconciliation": {"status": "PASS"},
        },
        "endpoint_verification": {"status": "PASS"},
        "execution_result_id": _id("5"),
    }
    result = SimpleNamespace(
        execution_result_id=_id("5"),
        to_document=lambda: full_document,
    )

    def run(*, authority_chain: Any) -> Any:
        assert authority_chain is chain
        calls.append("RUN_REGISTERED_CAMPAIGN")
        return result

    monkeypatch.setattr(
        cli.consumer,
        "run_registered_v072_campaign_v1",
        run,
    )

    assert cli.main([]) == 0
    assert calls == [
        "FINALIZE",
        "DERIVE_ANCHOR_CLAIM",
        "MINT_ANCHOR",
        "CONSTRUCT_CHAIN",
        "VERIFY_CHAIN",
        "PREPARE_EXECUTION_PLAN",
        "OPEN_ATTEMPT_JOURNAL",
        "JOURNAL_BIND_SOURCE",
        "RUN_REGISTERED_CAMPAIGN",
        "JOURNAL_COMPUTATION",
        "VERIFY_ATTEMPT_JOURNAL",
        "JOURNAL_OUTPUT_PUBLISHED",
        "VERIFY_ATTEMPT_JOURNAL",
        "CLOSE_ATTEMPT_JOURNAL",
    ]
    assert output.read_bytes() == canonical_json_bytes(full_document)
    assert list(output_parent.glob(".*.tmp")) == []
    summary = json.loads(capsys.readouterr().out)
    assert summary == {
        "schema": "acfqp.v072_registered_campaign_cli_result.v1",
        "schema_version": "1.0.0",
        "authority_chain_id": chain.chain_id,
        "execution_result_id": result.execution_result_id,
        "output_path": "artifacts/v072_registered_campaign_result_v1.json",
        "attempt_journal_id": _id("9"),
        "attempt_journal_closure": "OUTPUT_PUBLISHED",
    }


def test_campaign_exception_is_durably_caught_before_journal_close(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "artifacts").mkdir(parents=True)
    calls: list[str] = []
    chain, _, _ = _install_authority_boundaries(
        monkeypatch,
        root,
        calls,
    )
    writer = _install_journal_boundaries(
        monkeypatch,
        root=root,
        chain=chain,
        calls=calls,
    )
    injected = RuntimeError("injected campaign failure")

    def fail(*, authority_chain: Any) -> Any:
        assert authority_chain is chain
        calls.append("RUN_REGISTERED_CAMPAIGN")
        raise injected

    monkeypatch.setattr(
        cli.consumer,
        "run_registered_v072_campaign_v1",
        fail,
    )

    with pytest.raises(RuntimeError) as captured:
        cli.main([])

    assert captured.value is injected
    assert writer.caught_error is injected
    assert writer.caught_phase == "CAMPAIGN_EXECUTION"
    assert calls[-2:] == [
        "JOURNAL_CAUGHT_FAILURE",
        "CLOSE_ATTEMPT_JOURNAL",
    ]
    assert not (
        root / "artifacts" / "v072_registered_campaign_result_v1.json"
    ).exists()


def test_authority_only_verifies_chain_without_campaign_or_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "artifacts").mkdir(parents=True)
    calls: list[str] = []
    _, claim, anchor = _install_authority_boundaries(
        monkeypatch,
        root,
        calls,
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("campaign/source/target reconstruction was opened")

    monkeypatch.setattr(
        cli.consumer,
        "run_registered_v072_campaign_v1",
        forbidden,
    )
    monkeypatch.setattr(
        cli.final_authority,
        "finalize_v072_final_preregistration_v1",
        forbidden,
    )
    monkeypatch.setattr(
        cli.consumer,
        "RegisteredCampaignAuthorityChainV1",
        forbidden,
    )

    assert cli.main(["--check-authority-only"]) == 0
    assert calls == [
        "DERIVE_ANCHOR_CLAIM",
        "MINT_ANCHOR",
    ]
    report = json.loads(capsys.readouterr().out)
    assert report["remote_main_anchor_claim_id"] == claim.claim_id
    assert report["remote_main_anchor_id"] == anchor.anchor_id
    assert report["remote_main_authority_verified"] is True
    assert report["authority_chain_constructed"] is False
    assert report["campaign_executed"] is False
    assert report["source_reconstruction_executed"] is False
    assert report["target_execution_started"] is False
    assert list((root / "artifacts").iterdir()) == []


@pytest.mark.parametrize(
    "hostile_kind",
    ("existing", "destination_symlink", "parent_symlink", "outside"),
)
def test_invalid_output_is_rejected_before_any_authority_or_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hostile_kind: str,
) -> None:
    root = (tmp_path / "repo").resolve()
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    outside = tmp_path / "outside"
    outside.mkdir()
    output_argument = "artifacts/v072_registered_campaign_result_v1.json"
    if hostile_kind == "existing":
        (artifacts / "v072_registered_campaign_result_v1.json").write_text(
            "preserve",
            encoding="utf-8",
        )
    elif hostile_kind == "destination_symlink":
        foreign = outside / "foreign.json"
        foreign.write_text("foreign", encoding="utf-8")
        (
            artifacts / "v072_registered_campaign_result_v1.json"
        ).symlink_to(foreign)
    elif hostile_kind == "parent_symlink":
        (artifacts / "linked").symlink_to(
            outside,
            target_is_directory=True,
        )
        output_argument = "artifacts/linked/result.json"
    else:
        output_argument = "../outside/result.json"
    monkeypatch.setattr(cli, "_repository_root_v1", lambda: root)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("authority was opened for invalid output")

    monkeypatch.setattr(
        cli.final_authority,
        "finalize_v072_final_preregistration_v1",
        forbidden,
    )

    with pytest.raises(SystemExit):
        cli.main(["--output", output_argument])
    if hostile_kind == "existing":
        assert (
            artifacts / "v072_registered_campaign_result_v1.json"
        ).read_text(encoding="utf-8") == "preserve"


def test_raced_destination_is_not_overwritten_after_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "repo").resolve()
    artifacts = root / "artifacts"
    artifacts.mkdir(parents=True)
    output = artifacts / "v072_registered_campaign_result_v1.json"
    calls: list[str] = []
    chain, _, _ = _install_authority_boundaries(
        monkeypatch,
        root,
        calls,
    )
    writer = _install_journal_boundaries(
        monkeypatch,
        root=root,
        chain=chain,
        calls=calls,
        output_repository_path=(
            "artifacts/v072_registered_campaign_result_v1.json"
        ),
    )
    result = SimpleNamespace(
        execution_result_id=_id("5"),
        to_document=lambda: {"execution_result_id": _id("5")},
    )

    def run(*, authority_chain: Any) -> Any:
        assert authority_chain is chain
        output.write_text("raced", encoding="utf-8")
        return result

    monkeypatch.setattr(
        cli.consumer,
        "run_registered_v072_campaign_v1",
        run,
    )
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        cli.main([])
    assert output.read_text(encoding="utf-8") == "raced"
    assert list(artifacts.glob(".*.tmp")) == []
    assert writer.caught_phase == "OUTPUT_PUBLICATION"
    assert calls[-2:] == [
        "JOURNAL_CAUGHT_FAILURE",
        "CLOSE_ATTEMPT_JOURNAL",
    ]


def test_anchor_claim_rederivation_mismatch_fails_before_chain_or_campaign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "artifacts").mkdir(parents=True)
    calls: list[str] = []
    _install_authority_boundaries(monkeypatch, root, calls)
    mismatched = SimpleNamespace(claim_id=_id("9"))
    monkeypatch.setattr(
        cli.final_authority,
        "derive_v072_remote_main_anchor_claim_v1",
        lambda repository_root: mismatched,
    )

    with pytest.raises(SystemExit, match="changed the derived"):
        cli.main(["--check-authority-only"])
    assert calls == ["MINT_ANCHOR"]
