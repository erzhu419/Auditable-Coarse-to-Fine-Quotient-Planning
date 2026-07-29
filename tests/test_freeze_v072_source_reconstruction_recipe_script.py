from __future__ import annotations

import inspect
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest

from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1
from acfqp import v072_execution_environment_authority_v1 as environment_v1
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as environment_independent_v1,
)
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe_v1
from scripts import freeze_v072_source_reconstruction_recipe as cli


def _id(character: str) -> str:
    return character * 64


def _campaign() -> Any:
    counters = SimpleNamespace(
        counters_id=_id("a"),
        physical_unique_observer_draws=101,
        physical_unique_random_word_calls=107,
        physical_unique_rejections=6,
        base_model_build_count=11,
        coordinate_candidate_model_build_count=12,
        expansion_candidate_model_build_count=13,
        promoted_model_build_count=14,
    )
    return SimpleNamespace(campaign_id=_id("b"), counters=counters)


def _expected_output_ids() -> dict[str, str]:
    return {
        "source_campaign_id": _id("b"),
        "source_campaign_verification_id": _id("c"),
        "source_archive_id": _id("d"),
        "production_archive_verification_id": _id("e"),
        "independent_archive_attestation_id": _id("f"),
        "source_archive_component_id": _id("1"),
    }


def _recipe(
    identities: dict[str, str],
) -> Any:
    document = {
        "reconstruction_inputs": identities,
        "expected_output_ids": _expected_output_ids(),
    }
    return SimpleNamespace(
        recipe_id=_id("2"),
        replay_ready=True,
        to_document=lambda: document,
    )


def _identity_fixture(
    monkeypatch: pytest.MonkeyPatch,
    calls: list[str],
) -> tuple[dict[str, str], Any]:
    identities = {
        "component_tree_digest": _id("3"),
        "test_command_manifest_id": _id("4"),
        "runtime_dependency_lock_id": _id("5"),
        "interpreter_build_identity_id": _id("6"),
        "environment_independent_attestation_id": _id("7"),
    }
    environment = SimpleNamespace(
        test_command_manifest=SimpleNamespace(
            test_command_manifest_id=identities[
                "test_command_manifest_id"
            ],
        ),
        runtime_dependency_lock=SimpleNamespace(
            runtime_dependency_lock_id=identities[
                "runtime_dependency_lock_id"
            ],
        ),
        interpreter_build_identity=SimpleNamespace(
            interpreter_build_identity_id=identities[
                "interpreter_build_identity_id"
            ],
        ),
    )
    attestation = SimpleNamespace(
        attestation_id=identities[
            "environment_independent_attestation_id"
        ],
    )
    registry = SimpleNamespace(
        component_tree_digest=identities["component_tree_digest"],
    )

    def freeze_environment(root: Path) -> Any:
        assert root.is_absolute()
        calls.append("FREEZE_ENVIRONMENT")
        return environment

    def verify_environment(root: Path, value: Any) -> Any:
        assert value is environment
        calls.append("VERIFY_ENVIRONMENT")
        return attestation

    def freeze_registry(root: Path) -> Any:
        calls.append("FREEZE_COMPONENT_REGISTRY")
        return registry

    def verify_registry(root: Path, value: Any) -> Any:
        assert value is registry
        calls.append("VERIFY_COMPONENT_REGISTRY")
        return registry

    monkeypatch.setattr(
        environment_v1,
        "freeze_v072_execution_environment_authorities_v1",
        freeze_environment,
    )
    monkeypatch.setattr(
        environment_independent_v1,
        "verify_execution_environment_authorities_independently_v1",
        verify_environment,
    )
    monkeypatch.setattr(
        manifest_v1,
        "freeze_internal_component_registry_v1",
        freeze_registry,
    )
    monkeypatch.setattr(
        manifest_v1,
        "verify_component_registry_snapshot_v1",
        verify_registry,
    )
    return identities, environment


def test_cli_has_only_fixed_modes_and_no_evidence_or_identity_inputs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert tuple(inspect.signature(cli.main).parameters) == ("argv",)
    assert cli.RECIPE_RELATIVE_PATH == Path(
        manifest_v1.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("constructor was reached by a rejected argument")

    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    for arguments in (
        ("--recipe-id", _id("8")),
        ("--status", "PASS"),
        ("--path", "/tmp/foreign"),
        ("--max-workers", "1"),
    ):
        with pytest.raises(SystemExit) as captured:
            cli.main(list(arguments))
        assert captured.value.code == 2


def test_default_freeze_uses_fixed_path_workers_and_exact_call_order(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "specs").mkdir(parents=True)
    source_campaign = _campaign()
    source_verification = SimpleNamespace(verification_id=_id("c"))
    frozen_recipe = _recipe({})
    calls: list[str] = []

    monkeypatch.setattr(cli, "_repository_root", lambda: root)

    def run_campaign(*, max_workers: int) -> Any:
        assert max_workers == source_recipe_v1.RECONSTRUCTION_MAX_WORKERS
        calls.append("RUN_REGISTERED_SOURCE_CAMPAIGN")
        return source_campaign

    def verify_campaign(value: Any, *, max_workers: int) -> Any:
        assert value is source_campaign
        assert max_workers == source_recipe_v1.RECONSTRUCTION_MAX_WORKERS
        calls.append("VERIFY_REGISTERED_SOURCE_CAMPAIGN")
        return source_verification

    def write_recipe(
        path: Path,
        repository_root: Path,
        *,
        source_campaign: Any,
        source_verification: Any,
    ) -> Any:
        assert path == (
            root / "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
        )
        assert repository_root == root
        assert source_campaign is not None
        assert source_verification is not None
        calls.append("WRITE_SOURCE_RECIPE")
        return frozen_recipe

    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        run_campaign,
    )
    monkeypatch.setattr(
        campaign_v1,
        "verify_observation_support_campaign_v1",
        verify_campaign,
    )
    monkeypatch.setattr(
        source_recipe_v1,
        "write_source_reconstruction_recipe_v1",
        write_recipe,
    )

    assert cli.main([]) == 0
    assert calls == [
        "RUN_REGISTERED_SOURCE_CAMPAIGN",
        "VERIFY_REGISTERED_SOURCE_CAMPAIGN",
        "WRITE_SOURCE_RECIPE",
    ]
    output = json.loads(capsys.readouterr().out)
    assert output["recipe_id"] == frozen_recipe.recipe_id
    assert output["source_campaign_id"] == source_campaign.campaign_id
    assert output["source_campaign_verification_id"] == (
        source_verification.verification_id
    )
    assert output["work"]["physical_unique_observer_draws"] == 101


@pytest.mark.parametrize("hostile_kind", ("regular", "symlink"))
def test_default_freeze_refuses_overwrite_and_symlink_before_constructor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    hostile_kind: str,
) -> None:
    root = (tmp_path / "repo").resolve()
    specs = root / "specs"
    specs.mkdir(parents=True)
    path = specs / "V072_SOURCE_RECONSTRUCTION_RECIPE.json"
    if hostile_kind == "regular":
        path.write_text("existing", encoding="utf-8")
    else:
        target = tmp_path / "foreign.json"
        target.write_text("foreign", encoding="utf-8")
        path.symlink_to(target)
    monkeypatch.setattr(cli, "_repository_root", lambda: root)

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("heavy source constructor was opened")

    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    with pytest.raises(SystemExit, match="refusing to overwrite"):
        cli.main([])


def test_check_strictly_replays_nontarget_identities_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "specs").mkdir(parents=True)
    monkeypatch.setattr(cli, "_repository_root", lambda: root)
    calls: list[str] = []
    identities, _environment = _identity_fixture(monkeypatch, calls)
    frozen_recipe = _recipe(identities)

    def load(path: Path) -> Any:
        assert path == (
            root / "specs/V072_SOURCE_RECONSTRUCTION_RECIPE.json"
        )
        calls.append("STRICT_LOAD_RECIPE")
        return frozen_recipe

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("check mode opened held-out target work")

    monkeypatch.setattr(
        source_recipe_v1,
        "load_source_reconstruction_recipe_v1",
        load,
    )
    monkeypatch.setattr(
        source_recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        forbidden,
    )
    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    monkeypatch.setattr(
        campaign_v1,
        "verify_observation_support_campaign_v1",
        forbidden,
    )

    assert cli.main(["--check"]) == 0
    assert calls == [
        "STRICT_LOAD_RECIPE",
        "FREEZE_ENVIRONMENT",
        "VERIFY_ENVIRONMENT",
        "FREEZE_COMPONENT_REGISTRY",
        "VERIFY_COMPONENT_REGISTRY",
    ]
    output = json.loads(capsys.readouterr().out)
    assert output["recipe_id"] == frozen_recipe.recipe_id
    assert output["component_tree_digest"] == (
        identities["component_tree_digest"]
    )


def test_check_rejects_stale_identity_without_target_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "specs").mkdir(parents=True)
    monkeypatch.setattr(cli, "_repository_root", lambda: root)
    calls: list[str] = []
    identities, _environment = _identity_fixture(monkeypatch, calls)
    stale = dict(identities)
    stale["component_tree_digest"] = _id("9")
    monkeypatch.setattr(
        source_recipe_v1,
        "load_source_reconstruction_recipe_v1",
        lambda path: _recipe(stale),
    )

    def forbidden(*_args: Any, **_kwargs: Any) -> None:
        raise AssertionError("stale check opened held-out target work")

    monkeypatch.setattr(
        source_recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        forbidden,
    )
    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    with pytest.raises(SystemExit, match="identity is stale"):
        cli.main(["--check"])


def test_replay_is_the_only_existing_recipe_mode_that_runs_heavy_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = (tmp_path / "repo").resolve()
    (root / "specs").mkdir(parents=True)
    monkeypatch.setattr(cli, "_repository_root", lambda: root)
    calls: list[str] = []
    identities, _environment = _identity_fixture(monkeypatch, calls)
    frozen_recipe = _recipe(identities)
    source_campaign = _campaign()
    source_verification = SimpleNamespace(verification_id=_id("c"))

    def load(path: Path) -> Any:
        calls.append("STRICT_LOAD_RECIPE")
        return frozen_recipe

    def replay(repository_root: Path, recipe: Any) -> Any:
        assert repository_root == root
        assert recipe is frozen_recipe
        calls.append("EXPLICIT_HEAVY_REPLAY")
        return SimpleNamespace(
            source_campaign=source_campaign,
            source_verification=source_verification,
        )

    monkeypatch.setattr(
        source_recipe_v1,
        "load_source_reconstruction_recipe_v1",
        load,
    )
    monkeypatch.setattr(
        source_recipe_v1,
        "replay_source_reconstruction_recipe_v1",
        replay,
    )

    assert cli.main(["--replay"]) == 0
    assert calls == [
        "STRICT_LOAD_RECIPE",
        "FREEZE_ENVIRONMENT",
        "VERIFY_ENVIRONMENT",
        "FREEZE_COMPONENT_REGISTRY",
        "VERIFY_COMPONENT_REGISTRY",
        "EXPLICIT_HEAVY_REPLAY",
    ]
    output = json.loads(capsys.readouterr().out)
    assert output["recipe_id"] == frozen_recipe.recipe_id
    assert output["work"]["physical_unique_observer_draws"] == 101
