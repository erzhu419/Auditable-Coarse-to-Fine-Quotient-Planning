from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_positive_promoted_campaign_independent_verifier_v1 as verifier
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_positive_promoted_campaign_v1 import (
    positive_campaign,
)
from tests.test_construction_k7_positive_promoted_overlay_v1 import (
    positive_promoted,
)
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


def test_independent_surface_and_import_boundary_are_narrow() -> None:
    assert verifier.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(verifier.LOCAL_DOMAINS) == 1
    assert set(verifier.__all__) == {
        "ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "PositivePromotedCampaignDirectoryVerificationV1",
        "verify_positive_promoted_campaign_directory_bytes_v1",
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
        "construction_k7_positive_promoted_campaign_v1",
        "construction_k7_positive_promoted_occurrence_accounting_v1",
        "construction_k7_positive_promoted_stage_accounting_v1",
        "construction_k7_positive_promoted_overlay_v1",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.fixture(scope="module")
def independent_campaign(positive_campaign, positive_promoted):
    campaign, directory = positive_campaign
    source, lineage, exact_replay, source_verification, positive = positive_promoted
    result = verifier.verify_positive_promoted_campaign_directory_bytes_v1(
        source=source,
        lineage=lineage,
        exact_replay=exact_replay,
        source_verification=source_verification,
        positive_result_bytes=canonical_json_bytes(positive.to_document()),
        campaign_directory=directory,
        expected_preregistration_id=campaign.preregistration.preregistration_id,
        expected_closure_id=campaign.closure.closure_id,
    )
    return campaign, directory, result


def test_bytes_replay_closes_formal_occurrence_and_campaign(
    independent_campaign,
) -> None:
    campaign, _directory, result = independent_campaign
    document = result.to_document()
    assert document["campaign_preregistration_id"] == (
        campaign.preregistration.preregistration_id
    )
    assert document["occurrence_accounting_bundle_id"] == (
        campaign.occurrence_bundle.bundle_id
    )
    assert document["campaign_occurrence_row_id"] == campaign.occurrence_row.row_id
    assert document["campaign_closure_id"] == campaign.closure.closure_id
    assert document["work_vector_id"] == campaign.occurrence_bundle.work_vector.work_vector_id
    assert document["comparison_vector_id"] == (
        campaign.occurrence_bundle.comparison_vector.comparison_vector_id
    )
    assert document["io.output_bytes"] == campaign.occurrence_bundle.fixed_point.output_bytes
    assert document["registered_logical_occurrence_count"] == 1
    assert document["closed_logical_occurrence_count"] == 1
    assert document["plan_certificate_count"] == 1
    assert document["noncertificate_count"] == 0
    assert document["physical_output_fixed_point_equality_replayed"] is True
    assert document["producer_modules_imported"] is False
    assert document["official_execution_allowed"] is False
    assert document["valid"] is True


def test_all_nine_shared_values_and_abstract_route_survive_replay(
    independent_campaign,
) -> None:
    campaign, _directory, result = independent_campaign
    values = campaign.occurrence_bundle.work_vector.values
    assert values["common.hash_invocations"] > 0
    assert values["common.integrity_checks"] == 6
    assert values["common.protocol_checks"] == 5
    assert values["io.staged_bytes"] == 0
    assert values["process.launches"] == 0
    assert result.comparison_values == campaign.occurrence_bundle.comparison_vector.values
    assert all(
        value == 0
        for path, value in values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )


def test_resigned_denominator_deletion_is_rejected_before_expensive_replay(
    positive_campaign,
    positive_promoted,
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign, directory = positive_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    target = copied / "0003_CAMPAIGN_CLOSURE.json"
    document = loads_canonical_json(target.read_bytes())
    document["closure_denominator"] = 0
    payload = dict(document)
    payload.pop("campaign_closure_id")
    document["campaign_closure_id"] = content_id(
        CONSTRUCTION_K7_POSITIVE_PROMOTED_CAMPAIGN_CLOSURE_V1_DOMAIN,
        payload,
    )
    target.write_bytes(canonical_json_bytes(document))
    source, lineage, exact_replay, source_verification, positive = positive_promoted

    def forbidden(*_args, **_kwargs):
        raise AssertionError("denominator gate ran expensive positive replay")

    monkeypatch.setattr(
        verifier.positive_verifier_v1,
        "verify_positive_promoted_overlay_bytes_independently_v1",
        forbidden,
    )
    with pytest.raises(
        verifier.ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error,
        match="denominator gate",
    ):
        verifier.verify_positive_promoted_campaign_directory_bytes_v1(
            source=source,
            lineage=lineage,
            exact_replay=exact_replay,
            source_verification=source_verification,
            positive_result_bytes=canonical_json_bytes(positive.to_document()),
            campaign_directory=copied,
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=campaign.closure.closure_id,
        )


def test_missing_occurrence_role_is_rejected(positive_campaign, tmp_path: Path) -> None:
    _campaign, directory = positive_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    (copied / "occurrence-0001" / "WORK_VECTOR.json").unlink()
    with pytest.raises(
        verifier.ConstructionK7PositivePromotedCampaignIndependentVerifierV1Error
    ):
        verifier.verify_positive_promoted_campaign_directory_bytes_v1(
            source=object(),
            lineage=object(),
            exact_replay=object(),
            source_verification=object(),
            positive_result_bytes=b"{}",
            campaign_directory=copied,
            expected_preregistration_id="0" * 64,
            expected_closure_id="0" * 64,
        )
