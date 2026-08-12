from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_observation_driven_world_model_campaign_v1 as producer
from acfqp import (
    construction_k7_observation_driven_world_model_campaign_independent_verifier_v1
    as subject,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


@pytest.fixture(scope="session")
def campaign(tmp_path_factory):
    directory = tmp_path_factory.mktemp("world-model-independent") / "campaign"
    result = producer.run_observation_driven_world_model_campaign_v1(
        campaign_directory=directory
    )
    return result, directory


def test_verifier_import_surface_excludes_all_campaign_producers() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden = {
        "acfqp.construction_k7_observation_driven_world_model_campaign_v1",
        "acfqp.construction_k7_observation_driven_world_model_synthesis_v1",
        "acfqp.construction_k7_heldout_catalogue_query_router_v1",
        "acfqp.construction_k7_heldout_reusable_model_catalogue_v1",
        "acfqp.construction_k7_heldout_checkpoint_recertification_v1",
        "acfqp.construction_k7_heldout_k6_checkpoint_recertification_v1",
    }
    assert not (imported & forbidden)
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error",
        "EXPECTED_FILENAMES",
        "LOCAL_DOMAINS",
        "ObservationDrivenCampaignIndependentVerificationV1",
        "verify_observation_driven_campaign_directory_bytes_v1",
    }


def test_independent_replay_closes_both_models_routes_ood_and_denominators(
    campaign,
) -> None:
    result, directory = campaign
    verification = subject.verify_observation_driven_campaign_directory_bytes_v1(
        directory
    )
    document = verification.to_document()
    assert verification.preregistration_id == result.preregistration.preregistration_id
    assert verification.occurrence_ids == tuple(row.occurrence_id for row in result.rows)
    assert verification.closure_id == result.closure.closure_id
    assert document["producer_import_count"] == 0
    assert document["both_local_recovery_chains_independently_replayed"] is True
    assert document["two_exact_model_reuses_independently_replanned"] is True
    assert document["negative_control_no_access_independently_replayed"] is True
    assert document["catalogue_epoch_lineage_independently_replayed"] is True
    assert document["all_five_denominator_rows_retained"] is True
    assert document["physical_campaign_bytes_verified"] is True
    assert document["valid"] is True


def test_replay_is_deterministic_and_draws_no_new_observations(campaign) -> None:
    _result, directory = campaign
    first = subject.verify_observation_driven_campaign_directory_bytes_v1(directory)
    second = subject.verify_observation_driven_campaign_directory_bytes_v1(directory)
    assert first.verification_id == second.verification_id
    assert first.to_document() == second.to_document()


def test_semantically_forged_rehashed_closure_is_rejected(
    campaign, tmp_path: Path
) -> None:
    _result, directory = campaign
    copied = tmp_path / "forged-closure"
    shutil.copytree(directory, copied)
    target = copied / producer.CLOSURE_FILENAME
    document = loads_canonical_json(target.read_bytes())
    assert isinstance(document, dict)
    document["noncertificate_count"] = 0
    document.pop("campaign_closure_id")
    document["campaign_closure_id"] = content_id(
        CONSTRUCTION_K7_OBSERVATION_DRIVEN_CAMPAIGN_CLOSURE_V1_DOMAIN,
        document,
    )
    target.chmod(0o600)
    target.write_bytes(canonical_json_bytes(document))
    target.chmod(0o400)
    with pytest.raises(
        subject.ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error
    ):
        subject.verify_observation_driven_campaign_directory_bytes_v1(copied)


def test_deleted_denominator_row_is_rejected(campaign, tmp_path: Path) -> None:
    _result, directory = campaign
    copied = tmp_path / "deleted-row"
    shutil.copytree(directory, copied)
    (copied / producer.OCCURRENCE_FILENAMES[-1]).unlink()
    with pytest.raises(
        subject.ConstructionK7ObservationDrivenCampaignIndependentVerifierV1Error
    ):
        subject.verify_observation_driven_campaign_directory_bytes_v1(copied)


def test_producer_monkeypatch_cannot_change_bytes_only_replay(
    campaign, monkeypatch
) -> None:
    _result, directory = campaign

    def forbidden(*_args, **_kwargs):
        raise AssertionError("independent verifier invoked campaign producer")

    monkeypatch.setattr(
        producer, "run_observation_driven_world_model_campaign_v1", forbidden
    )
    verification = subject.verify_observation_driven_campaign_directory_bytes_v1(
        directory
    )
    assert verification.to_document()["valid"] is True
