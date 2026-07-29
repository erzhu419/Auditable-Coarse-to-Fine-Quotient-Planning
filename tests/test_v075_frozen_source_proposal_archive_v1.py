from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
import acfqp.v075_frozen_source_proposal_archive_v1 as v075


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


def _compiled() -> v075.V075FrozenSourceProposalArchiveV1:
    return v075.compile_v075_frozen_source_proposal_archive_v1(
        REPOSITORY_ROOT
    )


def _document() -> dict[str, object]:
    return json.loads(_compiled().canonical_bytes)


def _forbidden_paths(
    value: object,
    path: tuple[str, ...] = (),
) -> tuple[str, ...]:
    found: list[str] = []
    if type(value) is list:
        for index, item in enumerate(value):
            found.extend(_forbidden_paths(item, (*path, str(index))))
    elif type(value) is dict:
        for key, item in value.items():
            normalized = key.lower().replace("-", "_")
            if (
                any(
                    fragment in normalized
                    for fragment in ("target", "result", "certificate", "cache")
                )
                and key != "target_execution_allowed"
            ):
                found.append(".".join((*path, key)))
            found.extend(_forbidden_paths(item, (*path, key)))
    return tuple(found)


def test_domains_are_new_unique_and_role_separated() -> None:
    assert len(v075.DOMAIN_TAGS) == len(set(v075.DOMAIN_TAGS.values()))
    assert all(
        domain.startswith("acfqp:v075-")
        for domain in v075.DOMAIN_TAGS.values()
    )


def test_compile_freezes_exact_proposal_surface_and_upstream_chain() -> None:
    archive = _compiled()

    assert archive.source_recipe_id == v075.EXPECTED_SOURCE_RECIPE_ID
    assert archive.source_campaign_id == v075.EXPECTED_SOURCE_CAMPAIGN_ID
    assert (
        archive.source_campaign_verification_id
        == v075.EXPECTED_SOURCE_CAMPAIGN_VERIFICATION_ID
    )
    assert (
        archive.upstream_source_archive_id
        == v075.EXPECTED_UPSTREAM_SOURCE_ARCHIVE_ID
    )
    assert (
        archive.production_archive_verification_id
        == v075.EXPECTED_PRODUCTION_ARCHIVE_VERIFICATION_ID
    )
    assert (
        archive.independent_archive_attestation_id
        == v075.EXPECTED_INDEPENDENT_ARCHIVE_ATTESTATION_ID
    )
    assert (
        archive.source_archive_component_id
        == v075.EXPECTED_SOURCE_ARCHIVE_COMPONENT_ID
    )
    assert len(archive.consensus_summaries) == 7
    assert len(archive.applied_lookup) == 3
    assert archive.proposal_midrank_by_feature == {
        "9fe53537e8657540c657163cb437e1b3885a06a558ca27f0b92cb9d57135e28a":
            Fraction(1, 6),
        "7045f3287922411f0648501de97cc6c00ff6dad38fcd11ecf525e0a869e72a6a":
            Fraction(19, 36),
        "19ae3b19be43564c7781aab562d7e6261848f4b00e30cc7a65360a44056faadc":
            Fraction(1, 1),
    }
    assert archive.ordered_commitments.to_upstream_document() == (
        v075.EXPECTED_ORDERED_COMMITMENTS
    )


def test_archive_is_compact_proposal_only_and_has_zero_target_access() -> None:
    archive = _compiled()
    document = archive.to_document()

    assert len(archive.canonical_bytes) < 16_384
    assert document["source_only"] is True
    assert document["proposal_only"] is True
    assert document["may_certify"] is False
    assert document["target_execution_allowed"] is False
    assert document["observer_calls"] == 0
    assert document["environment_law_reads"] == 0
    assert document["source_campaign_reconstruction_calls"] == 0
    assert _forbidden_paths(document) == ()


def test_offline_work_is_identity_bound_but_not_fabricated() -> None:
    offline = _compiled().offline_work.to_document()

    assert (
        offline["source_campaign_counters_id"]
        == v075.EXPECTED_SOURCE_CAMPAIGN_COUNTERS_ID
    )
    assert offline["upstream_native_counter_vector_required"] is True
    assert offline["counter_values_inlined"] is False
    assert offline["zero_work_claimed"] is False
    assert offline["offline_work_retained"] is True
    assert (
        offline["offline_work_materialization_status"]
        == v075.OFFLINE_WORK_MATERIALIZATION_STATUS
        == "IDENTITY_BOUND_REPLAY_REQUIRED"
    )
    assert offline["target_execution_allowed"] is False
    assert not any("work_vector" in key for key in offline)


def test_strict_loader_and_independent_recipe_recompilation_round_trip() -> None:
    archive = _compiled()
    loaded = v075.load_v075_frozen_source_proposal_archive_v1(
        archive.canonical_bytes,
        expected_archive_id=archive.archive_id,
        expected_source_recipe_id=archive.source_recipe_id,
        expected_offline_work_reference_id=(
            archive.offline_work.work_reference_id
        ),
    )
    verification = (
        v075.verify_v075_frozen_source_proposal_archive_bytes_independently_v1(
            repository_root=REPOSITORY_ROOT,
            raw=archive.canonical_bytes,
        )
    )

    assert loaded == archive
    assert verification.archive_id == archive.archive_id
    assert verification.recomputed_archive_id == archive.archive_id
    assert len(verification.consensus_summary_ids) == 7
    assert len(verification.applied_lookup_ids) == 3
    assert verification.to_document()["tracked_recipe_recompiled"] is True
    assert (
        verification.to_document()["claimed_values_guided_recompilation"]
        is False
    )


def test_compiler_never_reconstructs_campaign_or_calls_observer(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("historical reconstruction/observation was called")

    monkeypatch.setattr(
        v075.v072_recipe,
        "replay_source_reconstruction_recipe_v1",
        forbidden,
    )
    monkeypatch.setattr(
        v075.v072_recipe.campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )

    archive = _compiled()
    assert archive.to_document()["source_campaign_reconstruction_calls"] == 0


@pytest.mark.parametrize(
    "fabricated",
    (
        None,
        0,
        "0" * 64,
    ),
)
def test_null_zero_or_fabricated_offline_work_vector_is_rejected(
    fabricated: object,
) -> None:
    archive = _compiled()
    document = json.loads(archive.canonical_bytes)
    document["offline_work"]["source_work_vector_id"] = fabricated

    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.load_v075_frozen_source_proposal_archive_v1(
            canonical_json_bytes(document),
            expected_archive_id=archive.archive_id,
            expected_source_recipe_id=archive.source_recipe_id,
            expected_offline_work_reference_id=(
                archive.offline_work.work_reference_id
            ),
        )


@pytest.mark.parametrize(
    ("path", "value"),
    (
        (("target_result_id",), "0" * 64),
        (("target_execution_allowed",), True),
        (("cached_plan_id",), "0" * 64),
        (("certificate_id",), "0" * 64),
    ),
)
def test_old_target_result_certificate_or_cache_injection_fails_closed(
    path: tuple[str, ...],
    value: object,
) -> None:
    archive = _compiled()
    document = json.loads(archive.canonical_bytes)
    document[path[0]] = value

    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.load_v075_frozen_source_proposal_archive_v1(
            canonical_json_bytes(document),
            expected_archive_id=archive.archive_id,
            expected_source_recipe_id=archive.source_recipe_id,
            expected_offline_work_reference_id=(
                archive.offline_work.work_reference_id
            ),
        )


def test_offline_reference_deletion_or_zero_work_claim_fails_closed() -> None:
    archive = _compiled()
    deleted = json.loads(archive.canonical_bytes)
    deleted.pop("offline_work")
    false_zero = json.loads(archive.canonical_bytes)
    false_zero["offline_work"]["zero_work_claimed"] = True

    for document in (deleted, false_zero):
        with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
            v075.load_v075_frozen_source_proposal_archive_v1(
                canonical_json_bytes(document),
                expected_archive_id=archive.archive_id,
                expected_source_recipe_id=archive.source_recipe_id,
                expected_offline_work_reference_id=(
                    archive.offline_work.work_reference_id
                ),
            )


def test_campaign_counter_role_confusion_and_domain_swap_fail_closed() -> None:
    archive = _compiled()
    wrong_counter = json.loads(archive.canonical_bytes)
    wrong_counter["offline_work"]["source_campaign_counters_id"] = (
        archive.upstream_source_archive_id
    )
    swapped_domain = json.loads(archive.canonical_bytes)
    swapped_domain["archive_id"] = archive.offline_work.work_reference_id

    for document in (wrong_counter, swapped_domain):
        with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
            v075.load_v075_frozen_source_proposal_archive_v1(
                canonical_json_bytes(document),
                expected_archive_id=archive.archive_id,
                expected_source_recipe_id=archive.source_recipe_id,
                expected_offline_work_reference_id=(
                    archive.offline_work.work_reference_id
                ),
            )


def test_coherently_resigned_claim_still_fails_independent_recompilation() -> None:
    archive = _compiled()
    mutated = replace(archive, source_recipe_bytes_sha256="f" * 64)

    assert mutated.archive_id != archive.archive_id
    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.verify_v075_frozen_source_proposal_archive_independently_v1(
            repository_root=REPOSITORY_ROOT,
            claimed=mutated,
        )


def test_noncanonical_archive_bytes_are_rejected() -> None:
    archive = _compiled()
    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.load_v075_frozen_source_proposal_archive_v1(
            archive.canonical_bytes + b"\n",
            expected_archive_id=archive.archive_id,
            expected_source_recipe_id=archive.source_recipe_id,
            expected_offline_work_reference_id=(
                archive.offline_work.work_reference_id
            ),
        )


def test_changed_tracked_recipe_fails_even_when_canonical(
    tmp_path: Path,
) -> None:
    root = tmp_path / "repository"
    specs = root / "specs"
    specs.mkdir(parents=True)
    source = (
        REPOSITORY_ROOT
        / v075.TRACKED_SOURCE_RECIPE_RELATIVE_PATH
    )
    document = json.loads(source.read_bytes())
    document["new_observer_draws"] = 1
    (specs / source.name).write_bytes(canonical_json_bytes(document))

    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.compile_v075_frozen_source_proposal_archive_v1(root.resolve())


def test_relative_root_and_linked_recipe_are_rejected(
    tmp_path: Path,
) -> None:
    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.compile_v075_frozen_source_proposal_archive_v1(Path("."))

    root = tmp_path / "repository"
    specs = root / "specs"
    specs.mkdir(parents=True)
    tracked = (
        REPOSITORY_ROOT
        / v075.TRACKED_SOURCE_RECIPE_RELATIVE_PATH
    )
    (specs / tracked.name).symlink_to(tracked)
    with pytest.raises(v075.V075FrozenSourceProposalArchiveViolation):
        v075.compile_v075_frozen_source_proposal_archive_v1(root.resolve())
