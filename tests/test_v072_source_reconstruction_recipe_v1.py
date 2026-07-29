from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from acfqp.phase3e_ids import canonical_json_bytes
from acfqp import observation_support_campaign_v1 as campaign_v1
from acfqp import v072_source_reconstruction_recipe_v1 as recipe_v1
from tests.test_verified_source_acquisition_archive_independent_verifier_v2 import (
    miniature_source_archive,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def mechanics_source(
    miniature_source_archive,
    monkeypatch: pytest.MonkeyPatch,
):
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
def mechanics_recipe(mechanics_source):
    source_campaign, source_verification = mechanics_source
    return recipe_v1.freeze_source_reconstruction_recipe_v1(
        REPOSITORY_ROOT,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )


def test_compact_recipe_contains_no_raw_observation_ids_and_stays_locked(
    mechanics_recipe,
) -> None:
    document = mechanics_recipe.to_document()
    assert mechanics_recipe.replay_ready is False
    assert document["source_graph_commitment_complete"] is False
    assert document["replay_blocker"] == recipe_v1.INCOMPLETE_BLOCKER
    assert document["raw_observation_ids_persisted"] is False
    assert document["caller_supplied_expected_ids_accepted"] is False
    assert document["caller_supplied_runner_accepted"] is False
    assert document["new_observer_draws"] == 0
    assert document["max_canonical_recipe_bytes"] == 16 * 1024 * 1024
    assert document["official_execution_allowed"] is False
    assert document["ordered_commitments"]["context_results"]["count"] == 0
    rendered = recipe_v1.render_source_reconstruction_recipe_v1(
        mechanics_recipe
    )
    assert len(rendered) < 2_000_000
    assert len(rendered) < recipe_v1.MAX_CANONICAL_RECIPE_BYTES


def test_recipe_freezer_and_replay_accept_no_ids_or_runner(
    mechanics_source,
) -> None:
    source_campaign, source_verification = mechanics_source
    freeze_signature = inspect.signature(
        recipe_v1.freeze_source_reconstruction_recipe_v1
    )
    assert tuple(freeze_signature.parameters) == (
        "repository_root",
        "source_campaign",
        "source_verification",
    )
    replay_signature = inspect.signature(
        recipe_v1.replay_source_reconstruction_recipe_v1
    )
    assert tuple(replay_signature.parameters) == (
        "repository_root",
        "recipe",
    )
    with pytest.raises(TypeError):
        recipe_v1.freeze_source_reconstruction_recipe_v1(
            REPOSITORY_ROOT,
            source_campaign=source_campaign,
            source_verification=source_verification,
            expected_campaign_id="a" * 64,  # type: ignore[call-arg]
        )


def test_recipe_round_trip_tamper_and_truncation(
    tmp_path: Path,
    mechanics_source,
) -> None:
    source_campaign, source_verification = mechanics_source
    path = (tmp_path / "source-recipe.json").resolve()
    written = recipe_v1.write_source_reconstruction_recipe_v1(
        path,
        REPOSITORY_ROOT,
        source_campaign=source_campaign,
        source_verification=source_verification,
    )
    loaded = recipe_v1.load_source_reconstruction_recipe_v1(path)
    assert loaded.to_document() == written.to_document()
    assert loaded.recipe_id == written.recipe_id

    tampered = written.to_document()
    tampered["expected_output_ids"]["source_archive_id"] = "0" * 64
    tamper_path = (tmp_path / "tampered.json").resolve()
    tamper_path.write_bytes(canonical_json_bytes(tampered))
    with pytest.raises(
        recipe_v1.V072SourceReconstructionRecipeInvariantViolation,
    ):
        recipe_v1.load_source_reconstruction_recipe_v1(tamper_path)

    truncated = (tmp_path / "truncated.json").resolve()
    truncated.write_bytes(path.read_bytes()[:-1])
    with pytest.raises(
        recipe_v1.V072SourceReconstructionRecipeInvariantViolation,
        match="strict canonical JSON",
    ):
        recipe_v1.load_source_reconstruction_recipe_v1(truncated)


def test_incomplete_mechanics_recipe_cannot_trigger_expensive_replay(
    mechanics_recipe,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("real campaign runner was called")

    monkeypatch.setattr(
        campaign_v1,
        "run_observation_support_campaign_v1",
        forbidden,
    )
    with pytest.raises(
        recipe_v1.V072SourceReconstructionRecipeInvariantViolation,
        match=recipe_v1.INCOMPLETE_BLOCKER,
    ):
        recipe_v1.replay_source_reconstruction_recipe_v1(
            REPOSITORY_ROOT,
            mechanics_recipe,
        )


def test_direct_recipe_construction_is_not_a_caller_id_channel(
    mechanics_recipe,
) -> None:
    with pytest.raises(
        recipe_v1.V072SourceReconstructionRecipeInvariantViolation,
        match="not internally frozen",
    ):
        recipe_v1.SourceReconstructionRecipeV1(
            object(),
            mechanics_recipe._payload_json,
        )
