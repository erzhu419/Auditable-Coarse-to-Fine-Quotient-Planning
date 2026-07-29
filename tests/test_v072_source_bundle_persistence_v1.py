from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import v072_source_bundle_persistence_v1 as persistence
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


@pytest.fixture
def mechanics_source(
    miniature_source_archive,
    monkeypatch: pytest.MonkeyPatch,
):
    """Make the intentionally partial miniature expose compact role docs."""

    source_campaign, source_verification, _ = miniature_source_archive

    def campaign_document(self):
        return {
            "schema": "acfqp.observation_support_campaign.v1",
            "campaign_id": self.campaign_id,
            "mechanics_fixture_only": True,
        }

    def verification_document(self):
        return {
            "schema": (
                "acfqp.observation_support_campaign_verification.v1"
            ),
            "campaign_id": self.campaign_id,
            "verification_id": self.verification_id,
            "mechanics_fixture_only": True,
        }

    monkeypatch.setattr(
        campaign_v1.ObservationSupportCampaignV1,
        "to_document",
        campaign_document,
    )
    monkeypatch.setattr(
        campaign_v1.ObservationSupportCampaignVerificationV1,
        "to_document",
        verification_document,
    )
    return source_campaign, source_verification


@pytest.fixture
def frozen_mechanics_bundle(mechanics_source):
    source_campaign, source_verification = mechanics_source
    return persistence.freeze_canonical_source_bundle_envelope_v1(
        source_campaign=source_campaign,
        source_verification=source_verification,
    )


def test_parser_registry_is_fixed_and_honestly_blocks_typed_replay() -> None:
    document = persistence.source_bundle_parser_registry_document_v1()
    assert document["parser_registry_id"] == persistence.PARSER_REGISTRY_ID
    assert document["typed_replay_ready"] is False
    assert document["typed_replay_blocker"] == (
        persistence.TYPED_REPLAY_BLOCKER
    )
    assert tuple(
        item["role"] for item in document["registrations"]
    ) == persistence.ROLE_ORDER
    assert all(
        item["typed_loader_available"] is False
        for item in document["registrations"]
    )


def test_bundle_freezer_accepts_only_source_objects_not_ids_or_artifacts(
    mechanics_source,
) -> None:
    source_campaign, source_verification = mechanics_source
    signature = inspect.signature(
        persistence.freeze_canonical_source_bundle_envelope_v1
    )
    assert tuple(signature.parameters) == (
        "source_campaign",
        "source_verification",
    )
    assert all(
        item not in signature.parameters
        for item in (
            "campaign_id",
            "verification_id",
            "archive",
            "archive_id",
            "component",
            "component_id",
        )
    )
    with pytest.raises(TypeError):
        persistence.freeze_canonical_source_bundle_envelope_v1(
            source_campaign=source_campaign,
            source_verification=source_verification,
            archive_id="a" * 64,  # type: ignore[call-arg]
        )


def test_canonical_bundle_round_trip_and_no_overwrite(
    tmp_path: Path,
    mechanics_source,
) -> None:
    source_campaign, source_verification = mechanics_source
    path = (tmp_path / "source-bundle.json").resolve()
    written = persistence.write_canonical_source_bundle_v1(
        path,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    loaded = persistence.load_canonical_source_bundle_envelope_v1(path)
    assert loaded == written
    assert loaded.bundle_id == written.bundle_id
    assert path.read_bytes() == persistence.render_canonical_source_bundle_v1(
        written
    )
    assert tuple(item.role for item in loaded.entries) == (
        persistence.ROLE_ORDER
    )
    assert all(
        item.full_typed_snapshot["kind"] == "TYPED_OBJECT"
        for item in loaded.entries
    )
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match="never overwrites",
    ):
        persistence.write_canonical_source_bundle_v1(
            path,
            source_campaign=source_campaign,
            source_verification=source_verification,
        )


def test_tamper_truncation_and_cross_role_attacks_fail_closed(
    tmp_path: Path,
    frozen_mechanics_bundle,
) -> None:
    baseline = frozen_mechanics_bundle.to_document()

    tampered = json.loads(json.dumps(baseline))
    tampered["entries"][0]["semantic_identity"] = "0" * 64
    tamper_path = (tmp_path / "tampered.json").resolve()
    tamper_path.write_bytes(canonical_json_bytes(tampered))
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
    ):
        persistence.load_canonical_source_bundle_envelope_v1(tamper_path)

    truncated_path = (tmp_path / "truncated.json").resolve()
    rendered = persistence.render_canonical_source_bundle_v1(
        frozen_mechanics_bundle
    )
    truncated_path.write_bytes(rendered[:-1])
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match="strict canonical JSON",
    ):
        persistence.load_canonical_source_bundle_envelope_v1(
            truncated_path
        )

    cross_role = json.loads(json.dumps(baseline))
    cross_role["entries"][0], cross_role["entries"][1] = (
        cross_role["entries"][1],
        cross_role["entries"][0],
    )
    cross_role_path = (tmp_path / "cross-role.json").resolve()
    cross_role_path.write_bytes(canonical_json_bytes(cross_role))
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match="reordered",
    ):
        persistence.load_canonical_source_bundle_envelope_v1(
            cross_role_path
        )


def test_noncanonical_and_symlink_bundle_inputs_fail_closed(
    tmp_path: Path,
    frozen_mechanics_bundle,
) -> None:
    canonical = persistence.render_canonical_source_bundle_v1(
        frozen_mechanics_bundle
    )
    noncanonical = (tmp_path / "pretty.json").resolve()
    noncanonical.write_bytes(canonical + b"\n")
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match="not canonical JSON",
    ):
        persistence.load_canonical_source_bundle_envelope_v1(noncanonical)

    target = (tmp_path / "target.json").resolve()
    target.write_bytes(canonical)
    link = tmp_path / "linked.json"
    link.symlink_to(target)
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match="symlink",
    ):
        persistence.load_canonical_source_bundle_envelope_v1(link)


def test_envelope_integrity_is_not_misrepresented_as_typed_replay(
    frozen_mechanics_bundle,
) -> None:
    assert frozen_mechanics_bundle.typed_replay_ready is False
    with pytest.raises(
        persistence.V072SourceBundlePersistenceInvariantViolation,
        match=persistence.TYPED_REPLAY_BLOCKER,
    ):
        persistence.replay_typed_source_bundle_v1(
            frozen_mechanics_bundle
        )
