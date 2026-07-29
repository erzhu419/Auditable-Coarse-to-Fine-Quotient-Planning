from __future__ import annotations

import json
from pathlib import Path
import shutil

import pytest

from acfqp import v075_tracked_source_authority_v1 as tracked
from acfqp import v075_confirmatory_manifest_preregistration_v1 as manifest
from acfqp import v075_source_prior_adapter_v1 as prior


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def test_all_eight_tracked_source_artifacts_replay_exactly() -> None:
    bundle, verification, bindings = (
        manifest.verify_and_bind_v075_tracked_source_authorities_v1(
            REPOSITORY_ROOT
        )
    )
    assert tuple(
        (item.role, item.repository_path) for item in bundle.artifacts
    ) == tracked.TRACKED_ARTIFACT_PATHS
    assert verification.bundle_id == bundle.bundle_id
    assert verification.source_prior_adapter_id == bundle.source_prior_adapter_id
    assert (
        verification.source_prior_verification_id
        == bundle.source_prior_verification_id
    )
    document = bundle.to_document()
    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["source_work_charged_once"] is True
    assert document["target_accessed"] is False
    assert tuple(item.role.value for item in bindings) == (
        "SOURCE_PRIOR_ADAPTER",
        "SOURCE_PRIOR_ADAPTER_VERIFICATION",
    )
    assert bindings[0].authority_id == bundle.source_prior_adapter_id
    assert (
        bindings[0].independent_verification_id
        == bundle.source_prior_verification_id
    )
    assert bindings[1].authority_id == bundle.source_prior_verification_id
    assert (
        bindings[1].independent_verification_id
        == verification.verification_id
    )


def _copy_source_tree(target: Path) -> None:
    (target / "specs").mkdir(parents=True)
    (target / "src" / "acfqp").mkdir(parents=True)
    for _role, relative in tracked.TRACKED_ARTIFACT_PATHS:
        source = REPOSITORY_ROOT / relative
        destination = target / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    # Archive recompilation reads the frozen recipe and package sources.
    shutil.copytree(
        REPOSITORY_ROOT / "src" / "acfqp",
        target / "src" / "acfqp",
        dirs_exist_ok=True,
    )
    shutil.copytree(
        REPOSITORY_ROOT / "specs",
        target / "specs",
        dirs_exist_ok=True,
    )


def test_tracked_source_mutation_fails_semantic_replay(tmp_path: Path) -> None:
    _copy_source_tree(tmp_path)
    candidate = tmp_path / "specs" / "V075_SOURCE_PRIOR_ADAPTER.json"
    value = json.loads(candidate.read_text(encoding="utf-8"))
    value["selector_use_authorized"] = False
    candidate.write_text(
        json.dumps(value, sort_keys=True, separators=(",", ":")),
        encoding="utf-8",
    )
    with pytest.raises(prior.V075SourcePriorAdapterViolation):
        tracked.verify_tracked_v075_source_authorities_v1(tmp_path)


def test_missing_or_symlinked_tracked_source_artifact_fails(
    tmp_path: Path,
) -> None:
    _copy_source_tree(tmp_path)
    candidate = (
        tmp_path
        / "specs"
        / "V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json"
    )
    candidate.unlink()
    candidate.symlink_to(
        REPOSITORY_ROOT
        / "specs"
        / "V075_SOURCE_PRIOR_ADAPTER_VERIFICATION.json"
    )
    with pytest.raises(
        tracked.V075TrackedSourceAuthorityInvariantViolation,
        match="symlink",
    ):
        tracked.verify_tracked_v075_source_authorities_v1(tmp_path)
