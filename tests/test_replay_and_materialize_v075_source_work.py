from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import inspect
from pathlib import Path
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
from typing import Iterator

import pytest

from scripts import replay_and_materialize_v075_source_work as controller


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
def _run(*argv: str, cwd: Path) -> bytes:
    result = subprocess.run(
        argv,
        cwd=cwd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(result.stderr.decode("utf-8", errors="replace"))
    return result.stdout


@pytest.fixture
def detached_snapshot(
    monkeypatch: pytest.MonkeyPatch,
) -> Iterator[Path]:
    del monkeypatch
    root = Path(tempfile.mkdtemp(prefix="acfqp-v075-source-", dir="/tmp"))
    clone = root / "source-snapshot"
    _run(
        "git",
        "clone",
        "-q",
        "--shared",
        "--no-checkout",
        str(REPOSITORY_ROOT),
        str(clone),
        cwd=root,
    )
    _run("git", "config", "user.name", "ACFQP Test", cwd=clone)
    _run("git", "config", "user.email", "acfqp@example.invalid", cwd=clone)
    _run(
        "git",
        "checkout",
        "--detach",
        "-q",
        controller.REQUIRED_SOURCE_REPLAY_COMMIT,
        cwd=clone,
    )
    try:
        yield clone
    finally:
        shutil.rmtree(root)


def _id(label: str) -> str:
    return hashlib.sha256(
        b"acfqp:v075-source-replay-controller-test:v1\x00"
        + label.encode("utf-8")
    ).hexdigest()


def test_controller_imports_only_stdlib_at_module_load_and_no_pickle() -> None:
    source = inspect.getsource(controller)
    tree = ast.parse(source)
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    assert not any(name == "acfqp" or name.startswith("acfqp.") for name in imported)
    assert "pickle" not in imported


def test_exact_clean_detached_snapshot_preflight(
    detached_snapshot: Path,
) -> None:
    result = controller.verify_snapshot_preflight_v1(detached_snapshot)

    assert result["detached_head"] is True
    assert result["clean_worktree"] is True
    assert result["frozen_recipe_environment"]["source_recipe_id"] == (
        controller.REQUIRED_SOURCE_RECIPE_ID
    )
    assert (
        result["frozen_recipe_environment"]["active_interpreter_checked"]
        is True
    )
    assert result["production_replay_eligible"] is True
    assert result["source_child_launched"] is False
    assert result["sample_draws_started"] is False
    assert result["target_access"] is False
    assert (
        result["source_only_bypass_evidence"][
            "confirmatory_manifest_import_forbidden"
        ]
        is True
    )


def test_attached_or_dirty_snapshot_fails_closed(
    detached_snapshot: Path,
) -> None:
    _run("git", "switch", "-q", "-c", "attack", cwd=detached_snapshot)
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="detached",
    ):
        controller.verify_snapshot_preflight_v1(detached_snapshot)

    _run("git", "checkout", "--detach", "-q", cwd=detached_snapshot)
    (detached_snapshot / "untracked.attack").write_text("attack")
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="not clean",
    ):
        controller.verify_snapshot_preflight_v1(detached_snapshot)


def test_recipe_byte_tamper_fails_even_after_coherent_git_commit(
    detached_snapshot: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    recipe = detached_snapshot / controller.RECIPE_PATH
    recipe.write_bytes(recipe.read_bytes() + b"\n")
    _run("git", "add", "--all", cwd=detached_snapshot)
    _run("git", "commit", "-q", "-m", "tamper", cwd=detached_snapshot)
    commit = _run(
        "git",
        "rev-parse",
        "HEAD",
        cwd=detached_snapshot,
    ).decode().strip()
    tree = _run(
        "git",
        "rev-parse",
        "HEAD^{tree}",
        cwd=detached_snapshot,
    ).decode().strip()
    monkeypatch.setattr(
        controller,
        "REQUIRED_SOURCE_REPLAY_COMMIT",
        commit,
    )
    monkeypatch.setattr(controller, "REQUIRED_SOURCE_REPLAY_TREE", tree)

    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="raw bytes changed",
    ):
        controller.verify_snapshot_preflight_v1(detached_snapshot)


def test_check_snapshot_is_fast_read_only_and_reports_not_run(
    detached_snapshot: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code = controller.main(
        [
            "--check-snapshot",
            "--snapshot-root",
            str(detached_snapshot),
        ]
    )
    output = capsys.readouterr()

    assert code == 0
    assert '"production_replay_status":"NOT_RUN"' in output.out
    assert '"production_materialization_status":"NOT_RUN"' in output.out
    assert '"source_child_launched":false' in output.out
    assert '"sample_draws_started":false' in output.out
    assert output.err == ""
    assert not any(detached_snapshot.glob("v075_source_*"))


def test_preflight_only_reports_readiness_without_replay(
    detached_snapshot: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def readiness(*_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "schema": "test.source_only_readiness.v1",
            "readiness_id": _id("readiness"),
            "ready": True,
            "sample_draws_started": False,
            "target_access": False,
        }

    monkeypatch.setattr(
        controller,
        "verify_source_only_replay_readiness_v1",
        readiness,
    )
    monkeypatch.setattr(
        controller,
        "_run_registered_source_only_protocol_v1",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("preflight started source replay")
        ),
    )
    assert controller.main(
        [
            "--preflight-only",
            "--snapshot-root",
            str(detached_snapshot),
        ]
    ) == 0
    output = capsys.readouterr()
    assert '"ready":true' in output.out
    assert '"sample_draws_started":false' in output.out
    assert output.err == ""


def test_source_only_readiness_loads_exact_types_but_draws_nothing(
    detached_snapshot: Path,
) -> None:
    preflight = controller.verify_snapshot_preflight_v1(detached_snapshot)
    manifest = controller.freeze_controller_code_manifest_v1()
    manifest.update(
        {
            "relevant_paths_clean": True,
            "all_paths_tracked": True,
            "tracked_paths": list(
                sorted(controller.CURRENT_PINNED_CODE_PATHS)
            ),
            "relevant_git_status_sha256": hashlib.sha256(b"").hexdigest(),
        }
    )
    manifest["controller_code_manifest_id"] = controller._role_id(
        "controller_code_manifest",
        {
            key: value
            for key, value in manifest.items()
            if key != "controller_code_manifest_id"
        },
    )
    result = controller.verify_source_only_replay_readiness_v1(
        detached_snapshot,
        preflight=preflight,
        code_manifest=manifest,
    )
    assert result["ready"] is True
    assert result["exact_historical_type_alignment_verified"] is True
    assert result["loaded_acfqp_modules"] == list(
        controller._SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST
    )
    assert result["sample_draws_started"] is False
    assert result["target_access"] is False


def test_explicit_replay_writes_only_three_canonical_bound_artifacts(
    detached_snapshot: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        controller,
        "verify_source_only_replay_readiness_v1",
        lambda *_args, **_kwargs: {
            "readiness_id": _id("readiness"),
        },
    )
    materialization = _FakeMaterialization(
        _id("materialization"),
        b'{"materialization":"fake"}',
    )
    verification = _FakeVerification(
        _id("verification"),
        materialization.materialization_id,
        materialization.materialization_id,
    )
    monkeypatch.setattr(
        controller,
        "_run_registered_source_only_protocol_v1",
        lambda **_kwargs: controller.InjectedProtocolResultV1(
            materialization,
            verification,
            {
                "protocol_id": _id("protocol"),
                "source_graph_verification_id": _id("source-graph"),
            },
        ),
    )
    output = tmp_path / "complete-output"
    code = controller.main(
        [
            "--replay-and-materialize",
            "--snapshot-root",
            str(detached_snapshot),
            "--output-dir",
            str(output),
        ]
    )
    printed = capsys.readouterr()

    assert code == 0
    assert printed.err == ""
    assert sorted(path.name for path in output.iterdir()) == sorted(
        (
            controller.STATUS_FILENAME,
            controller.MATERIALIZATION_FILENAME,
            controller.VERIFICATION_FILENAME,
        )
    )
    raw = (output / controller.STATUS_FILENAME).read_bytes()
    assert raw == controller._canonical_json_bytes(
        controller._strict_canonical_object(raw, "status")
    )
    assert (
        output / controller.MATERIALIZATION_FILENAME
    ).read_bytes() == materialization.canonical_bytes
    verification_raw = (
        output / controller.VERIFICATION_FILENAME
    ).read_bytes()
    assert verification_raw == controller._canonical_json_bytes(
        verification.to_document()
    )
    assert b'"production_replay_status":"COMPLETED"' in raw
    assert materialization.materialization_id.encode() in raw
    assert verification.verification_id.encode() in raw
    assert b'"target_access":false' in raw


def test_output_directory_cannot_be_reused(
    detached_snapshot: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    output = tmp_path / "existing"
    output.mkdir()

    assert controller.main(
        [
            "--replay-and-materialize",
            "--snapshot-root",
            str(detached_snapshot),
            "--output-dir",
            str(output),
        ]
    ) == 2
    assert "new absolute path" in capsys.readouterr().err


@pytest.mark.parametrize(
    "forbidden_argument",
    (
        "--counter-document",
        "--pickle",
        "--expected-materialization-id",
        "--target-root",
        "--runner",
        "--max-workers",
        "--reduced-work",
    ),
)
def test_cli_has_no_untrusted_replay_or_counter_override(
    forbidden_argument: str,
) -> None:
    with pytest.raises(SystemExit):
        controller._build_parser().parse_args(
            [
                "--check-snapshot",
                "--snapshot-root",
                "/tmp/source",
                forbidden_argument,
                "attack",
            ]
        )


def test_controller_manifest_binds_commit_tree_and_all_code_bytes() -> None:
    document = controller.freeze_controller_code_manifest_v1()

    assert len(document["repository_commit"]) == 40
    assert len(document["repository_tree"]) == 40
    assert tuple(
        item["repository_relative_path"] for item in document["files"]
    ) == controller.CURRENT_PINNED_CODE_PATHS
    for item in document["files"]:
        raw = (
            REPOSITORY_ROOT / item["repository_relative_path"]
        ).read_bytes()
        assert item["file_byte_count"] == len(raw)
        assert item["sha256_file_bytes"] == hashlib.sha256(raw).hexdigest()
    tracked = subprocess.run(
        (
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "ls-files",
            "--error-unmatch",
            "--",
            *controller.CURRENT_PINNED_CODE_PATHS,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    status = subprocess.run(
        (
            "git",
            "-C",
            str(REPOSITORY_ROOT),
            "status",
            "--porcelain=v1",
            "--untracked-files=all",
            "--",
            *controller.CURRENT_PINNED_CODE_PATHS,
        ),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=True,
    ).stdout
    assert document["all_paths_tracked"] is (tracked.returncode == 0)
    assert document["relevant_paths_clean"] is (status == b"")


def test_production_readiness_rejects_dirty_or_untracked_current_code() -> None:
    manifest = controller.freeze_controller_code_manifest_v1()
    manifest.update(
        {
            "relevant_paths_clean": True,
            "all_paths_tracked": True,
            "tracked_paths": list(
                sorted(controller.CURRENT_PINNED_CODE_PATHS)
            ),
            "relevant_git_status_sha256": hashlib.sha256(b"").hexdigest(),
        }
    )
    manifest["controller_code_manifest_id"] = controller._role_id(
        "controller_code_manifest",
        {
            key: value
            for key, value in manifest.items()
            if key != "controller_code_manifest_id"
        },
    )
    controller._require_production_code_manifest_v1(manifest)
    for field in ("relevant_paths_clean", "all_paths_tracked"):
        attacked = dict(manifest)
        attacked[field] = False
        attacked["controller_code_manifest_id"] = controller._role_id(
            "controller_code_manifest",
            {
                key: value
                for key, value in attacked.items()
                if key != "controller_code_manifest_id"
            },
        )
        with pytest.raises(
            controller.V075SourceReplayControllerViolation,
            match="tracked, clean",
        ):
            controller._require_production_code_manifest_v1(attacked)


def test_source_only_import_guard_and_exact_allowlist_fail_closed() -> None:
    guard = controller._SourceOnlyImportGuard()
    for name in (
        "acfqp.v072_confirmatory_execution_manifest_v1",
        "acfqp.v072_registered_target_selector_v1",
        "acfqp.heldout_graph_transition_observer_v2",
    ):
        with pytest.raises(ImportError, match="denied forbidden module"):
            guard.find_spec(name, None)
    controller._verify_loaded_module_allowlist_v1(
        controller._SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST
    )
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="exact allowlist",
    ):
        controller._verify_loaded_module_allowlist_v1(
            (
                *controller._SOURCE_ONLY_ACFQP_IMPORT_ALLOWLIST,
                "acfqp.unregistered_attack",
            )
        )


def test_reduced_source_graph_checks_ids_merkle_and_compact_artifacts() -> None:
    class Campaign:
        pass

    class CampaignVerification:
        pass

    class Archive:
        def to_document(self) -> dict[str, str]:
            return {"archive_id": self.archive_id}

    class Production:
        def to_document(self) -> dict[str, str]:
            return {"verification_id": self.verification_id}

    class Independent:
        def to_document(self) -> dict[str, str]:
            return {"verification_id": self.verification_id}

    class Component:
        def to_document(self) -> dict[str, object]:
            return {
                "component_id": self.component_id,
                "archive": {"archive_id": archive.archive_id},
                "production_verification": {
                    "verification_id": production.verification_id,
                },
                "independent_attestation": {
                    "verification_id": independent.verification_id,
                },
            }

    campaign = Campaign()
    campaign.campaign_id = _id("source-campaign")
    campaign.context_results = [
        SimpleNamespace(context_result_id=_id("context-0")),
        SimpleNamespace(context_result_id=_id("context-1")),
    ]
    campaign.family_manifest = SimpleNamespace(
        manifest_id=_id("family-manifest")
    )
    campaign.family_authority = SimpleNamespace(
        authority_id=_id("family-authority")
    )
    campaign.counters = SimpleNamespace(counters_id=_id("counters"))

    verification = CampaignVerification()
    verification.verification_id = _id("campaign-verification")
    verification.replayed_row_ids = (
        _id("row-0"),
        _id("row-1"),
        _id("row-2"),
    )

    archive = Archive()
    archive.archive_id = _id("archive")
    archive.adjacent_pairs = (
        SimpleNamespace(pair_id=_id("pair-0")),
    )
    archive.trials = (
        SimpleNamespace(trial_id=_id("trial-0")),
        SimpleNamespace(trial_id=_id("trial-1")),
    )
    archive.consensus = (
        SimpleNamespace(consensus_id=_id("consensus-0")),
    )
    production = Production()
    production.verification_id = _id("production")
    independent = Independent()
    independent.verification_id = _id("independent")
    component = Component()
    component.component_id = _id("component")
    recipe = SimpleNamespace(recipe_id=_id("recipe"))

    output_ids = {
        "source_campaign_id": campaign.campaign_id,
        "source_campaign_verification_id": verification.verification_id,
        "source_archive_id": archive.archive_id,
        "production_archive_verification_id": production.verification_id,
        "independent_archive_attestation_id": independent.verification_id,
        "source_archive_component_id": component.component_id,
    }
    commitments = {
        "context_results": controller._ordered_merkle_commitment_v1(
            tuple(x.context_result_id for x in campaign.context_results),
            role="CONTEXT_RESULT_IDS",
        ),
        "replayed_source_rows": controller._ordered_merkle_commitment_v1(
            verification.replayed_row_ids,
            role="REPLAYED_SOURCE_ROW_IDS",
        ),
        "archive_adjacent_pairs": (
            controller._ordered_merkle_commitment_v1(
                tuple(x.pair_id for x in archive.adjacent_pairs),
                role="ARCHIVE_ADJACENT_PAIR_IDS",
            )
        ),
        "archive_trials": controller._ordered_merkle_commitment_v1(
            tuple(x.trial_id for x in archive.trials),
            role="ARCHIVE_TRIAL_IDS",
        ),
        "archive_feature_consensus": (
            controller._ordered_merkle_commitment_v1(
                tuple(x.consensus_id for x in archive.consensus),
                role="ARCHIVE_FEATURE_CONSENSUS_IDS",
            )
        ),
        "family_manifest_id": campaign.family_manifest.manifest_id,
        "family_authority_id": campaign.family_authority.authority_id,
        "campaign_counters_id": campaign.counters.counters_id,
    }
    compact = {
        "source_archive": archive.to_document(),
        "production_archive_verification": production.to_document(),
        "independent_archive_attestation": independent.to_document(),
        "source_archive_component_summary": {
            "component_id": component.component_id,
        },
    }
    recipe_document = {
        "expected_output_ids": output_ids,
        "ordered_commitments": commitments,
        "compact_derived_artifacts": compact,
    }
    modules = SimpleNamespace(
        campaign_v1=SimpleNamespace(
            ObservationSupportCampaignV1=Campaign,
            ObservationSupportCampaignVerificationV1=CampaignVerification,
        ),
        archive_v2=SimpleNamespace(
            VerifiedSourceAcquisitionArchiveV2=Archive,
            VerifiedSourceAcquisitionArchiveVerificationV2=Production,
        ),
        independent_v2=SimpleNamespace(
            IndependentSourceAcquisitionArchiveVerificationV2=Independent,
        ),
        component_v1=SimpleNamespace(
            V072VerifiedSourceArchiveComponentV1=Component,
        ),
    )
    result = controller._verify_replayed_source_graph_v1(
        recipe=recipe,
        recipe_document=recipe_document,
        recipe_module=modules,
        source_campaign=campaign,
        source_verification=verification,
        archive=archive,
        production=production,
        independent=independent,
        component=component,
    )
    assert result["valid"] is True
    assert result["confirmatory_manifest_imported"] is False
    assert result["target_access"] is False

    attacked = dict(recipe_document)
    attacked["ordered_commitments"] = {
        **commitments,
        "archive_trials": commitments["archive_feature_consensus"],
    }
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="ordered commitments",
    ):
        controller._verify_replayed_source_graph_v1(
            recipe=recipe,
            recipe_document=attacked,
            recipe_module=modules,
            source_campaign=campaign,
            source_verification=verification,
            archive=archive,
            production=production,
            independent=independent,
            component=component,
        )


@dataclass(frozen=True)
class _FakeMaterialization:
    materialization_id: str
    canonical_bytes: bytes

    @property
    def source_recipe_id(self) -> str:
        return _id("recipe")


@dataclass(frozen=True)
class _FakeVerification:
    verification_id: str
    materialization_id: str
    recomputed_materialization_id: str

    def to_document(self) -> dict[str, str]:
        return {
            "schema": "test.fake_verification.v1",
            "materialization_id": self.materialization_id,
            "recomputed_materialization_id": (
                self.recomputed_materialization_id
            ),
            "verification_id": self.verification_id,
        }


class _FakeMaterializer:
    def __init__(self, order: list[str]) -> None:
        self.order = order

    def materialize(self, replay: object) -> _FakeMaterialization:
        assert replay is self.order
        self.order.append("materialize")
        return _FakeMaterialization(_id("materialization"), b"{}")

    def verify(
        self,
        *,
        replay: object,
        claimed: _FakeMaterialization,
    ) -> _FakeVerification:
        assert replay is self.order
        assert claimed.materialization_id == _id("materialization")
        self.order.append("verify")
        return _FakeVerification(
            _id("verification"),
            claimed.materialization_id,
            claimed.materialization_id,
        )


class _FakeMechanics:
    target_accessed = False
    hidden_law_accessed = False

    def __init__(self) -> None:
        self.order: list[str] = []

    def check_frozen_environment(self) -> str:
        self.order.append("environment")
        return "frozen-environment"

    def replay_exact_source(self) -> list[str]:
        assert self.order == ["environment"]
        self.order.append("replay")
        return self.order

    def load_current_v075_materializer(self) -> _FakeMaterializer:
        assert self.order == ["environment", "replay"]
        self.order.append("load-current")
        return _FakeMaterializer(self.order)


def test_injected_future_protocol_keeps_replay_and_materialization_in_process() -> None:
    mechanics = _FakeMechanics()
    result = controller._run_injected_same_process_protocol_v1(mechanics)

    assert mechanics.order == [
        "environment",
        "replay",
        "load-current",
        "materialize",
        "verify",
    ]
    assert result.materialization.materialization_id == _id(
        "materialization"
    )
    assert result.verification.materialization_id == (
        result.materialization.materialization_id
    )
    assert result.protocol_document["process_id_stable"] is True
    assert result.protocol_document["pickle_transport_accepted"] is False
    assert result.protocol_document["target_access"] is False


def test_injected_protocol_rejects_target_or_hidden_law_access() -> None:
    mechanics = _FakeMechanics()
    mechanics.target_accessed = True
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="target or hidden law",
    ):
        controller._run_injected_same_process_protocol_v1(mechanics)


def test_injected_protocol_rejects_open_verification_chain() -> None:
    class BrokenMaterializer(_FakeMaterializer):
        def verify(
            self,
            *,
            replay: object,
            claimed: _FakeMaterialization,
        ) -> _FakeVerification:
            self.order.append("verify")
            return _FakeVerification(
                _id("verification"),
                _id("foreign"),
                _id("foreign"),
            )

    mechanics = _FakeMechanics()
    mechanics.load_current_v075_materializer = lambda: BrokenMaterializer(
        mechanics.order
    )
    with pytest.raises(
        controller.V075SourceReplayControllerViolation,
        match="identity chain",
    ):
        controller._run_injected_same_process_protocol_v1(mechanics)
