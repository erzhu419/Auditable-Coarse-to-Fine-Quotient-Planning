#!/usr/bin/env python3
"""Freeze, check, or explicitly replay the registered V0-072 source recipe."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import v072_confirmatory_execution_manifest_v1 as manifest_v1
from acfqp import v072_execution_environment_authority_v1 as environment_v1
from acfqp import (
    v072_execution_environment_independent_verifier_v1
    as environment_independent_v1,
)
from acfqp import v072_source_reconstruction_recipe_v1 as source_recipe_v1


RECIPE_RELATIVE_PATH = Path(
    manifest_v1.SOURCE_RECONSTRUCTION_RECIPE_REPOSITORY_PATH
)


def _repository_root() -> Path:
    root = Path(__file__).resolve().parents[1]
    if not root.is_absolute() or not root.is_dir() or root.is_symlink():
        raise SystemExit("repository root is not one absolute real directory")
    return root


def _recipe_path(root: Path) -> Path:
    return root / RECIPE_RELATIVE_PATH


def _require_new_recipe_path(path: Path) -> None:
    if path.exists() or path.is_symlink():
        raise SystemExit(
            "refusing to overwrite or follow the frozen source recipe path"
        )
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise SystemExit("source recipe parent is not one real directory")


def _work_summary(source_campaign: Any) -> dict[str, int | str]:
    counters = source_campaign.counters
    return {
        "campaign_counters_id": counters.counters_id,
        "physical_unique_observer_draws": (
            counters.physical_unique_observer_draws
        ),
        "physical_unique_random_word_calls": (
            counters.physical_unique_random_word_calls
        ),
        "physical_unique_rejections": (
            counters.physical_unique_rejections
        ),
        "base_model_build_count": counters.base_model_build_count,
        "coordinate_candidate_model_build_count": (
            counters.coordinate_candidate_model_build_count
        ),
        "expansion_candidate_model_build_count": (
            counters.expansion_candidate_model_build_count
        ),
        "promoted_model_build_count": (
            counters.promoted_model_build_count
        ),
    }


def _recipe_output_summary(
    *,
    recipe: Any,
    source_campaign: Any | None = None,
    source_verification: Any | None = None,
) -> dict[str, Any]:
    document = recipe.to_document()
    summary: dict[str, Any] = {
        "recipe_id": recipe.recipe_id,
        **document["expected_output_ids"],
    }
    if source_campaign is not None:
        summary["source_campaign_id"] = source_campaign.campaign_id
        summary["work"] = _work_summary(source_campaign)
    if source_verification is not None:
        summary["source_campaign_verification_id"] = (
            source_verification.verification_id
        )
    return summary


def _current_environment_identity_summary(
    *,
    root: Path,
    recipe: Any,
) -> dict[str, str]:
    """Recompute only code/runtime identities; never open a target stream."""

    environment = (
        environment_v1.freeze_v072_execution_environment_authorities_v1(
            root
        )
    )
    environment_attestation = (
        environment_independent_v1
        .verify_execution_environment_authorities_independently_v1(
            root,
            environment,
        )
    )
    registry = manifest_v1.freeze_internal_component_registry_v1(root)
    registry = manifest_v1.verify_component_registry_snapshot_v1(
        root,
        registry,
    )
    current = {
        "component_tree_digest": registry.component_tree_digest,
        "test_command_manifest_id": (
            environment.test_command_manifest.test_command_manifest_id
        ),
        "runtime_dependency_lock_id": (
            environment.runtime_dependency_lock.runtime_dependency_lock_id
        ),
        "interpreter_build_identity_id": (
            environment.interpreter_build_identity
            .interpreter_build_identity_id
        ),
        "environment_independent_attestation_id": (
            environment_attestation.attestation_id
        ),
    }
    frozen = recipe.to_document()["reconstruction_inputs"]
    if any(frozen[name] != value for name, value in current.items()):
        raise SystemExit(
            "frozen source recipe environment/component identity is stale"
        )
    return current


def _print_summary(summary: dict[str, Any]) -> None:
    print(
        json.dumps(
            summary,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )


def _freeze(root: Path, path: Path) -> int:
    _require_new_recipe_path(path)
    source_campaign = campaign_v1.run_observation_support_campaign_v1(
        max_workers=source_recipe_v1.RECONSTRUCTION_MAX_WORKERS
    )
    source_verification = (
        campaign_v1.verify_observation_support_campaign_v1(
            source_campaign,
            max_workers=source_recipe_v1.RECONSTRUCTION_MAX_WORKERS,
        )
    )
    recipe = source_recipe_v1.write_source_reconstruction_recipe_v1(
        path,
        root,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    if recipe.replay_ready is not True:
        raise SystemExit("written source reconstruction recipe is not replay-ready")
    _print_summary(
        _recipe_output_summary(
            recipe=recipe,
            source_campaign=source_campaign,
            source_verification=source_verification,
        )
    )
    return 0


def _check(root: Path, path: Path) -> int:
    recipe = source_recipe_v1.load_source_reconstruction_recipe_v1(path)
    if recipe.replay_ready is not True:
        raise SystemExit("frozen source reconstruction recipe is not replay-ready")
    identities = _current_environment_identity_summary(
        root=root,
        recipe=recipe,
    )
    _print_summary(
        {
            "recipe_id": recipe.recipe_id,
            **recipe.to_document()["expected_output_ids"],
            **identities,
        }
    )
    return 0


def _replay(root: Path, path: Path) -> int:
    recipe = source_recipe_v1.load_source_reconstruction_recipe_v1(path)
    _current_environment_identity_summary(root=root, recipe=recipe)
    replay = source_recipe_v1.replay_source_reconstruction_recipe_v1(
        root,
        recipe,
    )
    _print_summary(
        _recipe_output_summary(
            recipe=recipe,
            source_campaign=replay.source_campaign,
            source_verification=replay.source_verification,
        )
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--check",
        action="store_true",
        help="strictly check the frozen recipe and current non-target identities",
    )
    mode.add_argument(
        "--replay",
        action="store_true",
        help="explicitly rerun the heavy registered source reconstruction",
    )
    args = parser.parse_args(argv)
    root = _repository_root()
    path = _recipe_path(root)
    if args.check:
        return _check(root, path)
    if args.replay:
        return _replay(root, path)
    return _freeze(root, path)


if __name__ == "__main__":
    raise SystemExit(main())
