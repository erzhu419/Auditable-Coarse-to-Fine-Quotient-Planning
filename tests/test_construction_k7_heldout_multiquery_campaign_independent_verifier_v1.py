from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_heldout_multiquery_campaign_independent_verifier_v1
    as verifier,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_heldout_multiquery_campaign_v1 import (
    multiquery_campaign,
)


def test_independent_surface_does_not_import_any_multiquery_producer() -> None:
    assert verifier.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(verifier.LOCAL_DOMAINS) == 1
    assert set(verifier.__all__) == {
        "ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error",
        "HeldoutMultiqueryCampaignIndependentVerificationV1",
        "LOCAL_DOMAINS",
        "verify_heldout_multiquery_campaign_directory_bytes_v1",
    }
    tree = ast.parse(Path(verifier.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    forbidden = (
        "construction_k7_heldout_multiquery_campaign_v1",
        "construction_k7_heldout_abstract_occurrence_accounting_v1",
        "construction_k7_heldout_abstract_stage_accounting_v1",
        "construction_k7_heldout_overlay_abstract_reuse_v1",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.fixture(scope="module")
def independent_multiquery_campaign(multiquery_campaign):
    campaign, directory, _calls = multiquery_campaign
    result = verifier.verify_heldout_multiquery_campaign_directory_bytes_v1(
        campaign_directory=directory,
        expected_preregistration_id=campaign.preregistration.preregistration_id,
        expected_closure_id=campaign.closure.closure_id,
    )
    return campaign, directory, result


def test_two_physical_occurrences_replay_to_one_shared_world_model(
    independent_multiquery_campaign,
) -> None:
    campaign, _directory, result = independent_multiquery_campaign
    document = result.to_document()
    assert document["campaign_preregistration_id"] == (
        campaign.preregistration.preregistration_id
    )
    assert document["ordered_occurrence_row_ids"] == [
        row.row_id for row in campaign.rows
    ]
    assert document["campaign_closure_id"] == campaign.closure.closure_id
    assert document["source_overlay_id"] == campaign.source.final_overlay.overlay_id
    assert document["quotient_model_id"] == (
        campaign.source.final_overlay.bridge.quotient_model.model_id
    )
    assert len(set(document["ordered_occurrence_verification_ids"])) == 2
    assert document["all_occurrences_independently_replayed"] is True
    assert document["single_query_neutral_overlay_reused"] is True
    assert document["producer_modules_imported"] is False
    assert document["valid"] is True


def test_independent_cumulative_vector_matches_campaign(
    independent_multiquery_campaign,
) -> None:
    campaign, _directory, result = independent_multiquery_campaign
    assert result.cumulative_comparison_values == (
        campaign.closure.cumulative_comparison_values
    )
    assert result.output_bytes == sum(
        row.occurrence_bundle.fixed_point.output_bytes for row in campaign.rows
    )
    document = result.to_document()
    assert document["registered_logical_occurrence_count"] == 2
    assert document["closed_logical_occurrence_count"] == 2
    assert document["closure_denominator"] == 2
    assert document["certificate_coverage_denominator"] == 2
    assert document["future_economics_cost_denominator"] == 2
    assert document["plan_certificate_count"] == 2
    assert document["noncertificate_count"] == 0
    assert document["official_execution_allowed"] is False


def test_resigned_denominator_deletion_fails_before_occurrence_replay(
    multiquery_campaign,
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign, directory, _calls = multiquery_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    target = copied / "0004_CAMPAIGN_CLOSURE.json"
    document = loads_canonical_json(target.read_bytes())
    document["closure_denominator"] = 1
    payload = dict(document)
    payload.pop("campaign_closure_id")
    document["campaign_closure_id"] = content_id(
        CONSTRUCTION_K7_HELDOUT_MULTIQUERY_CAMPAIGN_CLOSURE_V1_DOMAIN,
        payload,
    )
    target.write_bytes(canonical_json_bytes(document))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("cheap denominator gate ran occurrence replay")

    monkeypatch.setattr(
        verifier.occurrence_verifier_v1,
        "verify_heldout_abstract_occurrence_directory_bytes_v1",
        forbidden,
    )
    with pytest.raises(
        verifier.ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error,
        match="denominator gate",
    ):
        verifier.verify_heldout_multiquery_campaign_directory_bytes_v1(
            campaign_directory=copied,
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=campaign.closure.closure_id,
        )


def test_missing_physical_work_vector_is_rejected(
    multiquery_campaign, tmp_path: Path
) -> None:
    campaign, directory, _calls = multiquery_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    (copied / "occurrence-0002" / "WORK_VECTOR.json").unlink()
    with pytest.raises(
        verifier.ConstructionK7HeldoutMultiqueryCampaignIndependentVerifierV1Error
    ):
        verifier.verify_heldout_multiquery_campaign_directory_bytes_v1(
            campaign_directory=copied,
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=campaign.closure.closure_id,
        )
