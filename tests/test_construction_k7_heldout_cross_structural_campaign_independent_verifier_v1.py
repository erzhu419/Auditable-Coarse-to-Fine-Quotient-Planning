from __future__ import annotations

import ast
from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_heldout_cross_structural_campaign_independent_verifier_v1
    as verifier,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN,
    CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    content_id,
    canonical_json_bytes,
    loads_canonical_json,
)
from tests.test_construction_k7_heldout_cross_structural_campaign_v1 import (
    child_campaigns,
    cross_structural_campaign,
)


def _resign(document: dict, id_field: str, domain: str) -> dict:
    payload = dict(document)
    payload.pop(id_field, None)
    return {**payload, id_field: content_id(domain, payload)}


def _cached_child_verifications(campaign):
    w5 = loads_canonical_json(campaign.rows[0].child_verification_bytes)
    k6 = loads_canonical_json(campaign.rows[1].child_verification_bytes)
    w5_value = verifier.w5_verifier_v1.HeldoutAbstractCampaignDirectoryVerificationV1(
        w5["heldout_overlay_abstract_reuse_independent_verification_id"],
        w5["campaign_preregistration_id"],
        w5["occurrence_accounting_bundle_id"],
        w5["campaign_occurrence_row_id"],
        w5["campaign_closure_id"],
        w5["work_vector_id"],
        w5["comparison_vector_id"],
        w5["io.output_bytes"],
        tuple((row["axis"], row["value"]) for row in w5["comparison_values"]),
    )
    k6_value = verifier.k6_verifier_v1.HeldoutK6AbstractCampaignDirectoryVerificationV1(
        k6["heldout_k6_overlay_abstract_reuse_independent_verification_id"],
        k6["campaign_preregistration_id"],
        k6["occurrence_accounting_bundle_id"],
        k6["campaign_occurrence_row_id"],
        k6["campaign_closure_id"],
        k6["work_vector_id"],
        k6["comparison_vector_id"],
        k6["io.output_bytes"],
        tuple((row["axis"], row["value"]) for row in k6["comparison_values"]),
    )
    return w5_value, k6_value


@pytest.fixture(scope="module")
def independent_cross_structural_campaign(
    child_campaigns,
    cross_structural_campaign,
):
    campaign, directory = cross_structural_campaign
    result = verifier.verify_heldout_cross_structural_campaign_directory_bytes_v1(
        campaign_directory=directory,
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
        k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
        expected_preregistration_id=campaign.preregistration.preregistration_id,
        expected_closure_id=campaign.closure.closure_id,
    )
    return campaign, directory, result


def test_independent_surface_and_import_boundary_are_narrow() -> None:
    assert verifier.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(verifier.LOCAL_DOMAINS) == 1
    assert set(verifier.__all__) == {
        "ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error",
        "HeldoutCrossStructuralCampaignIndependentVerificationV1",
        "LOCAL_DOMAINS",
        "verify_heldout_cross_structural_campaign_directory_bytes_v1",
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
        "construction_k7_heldout_cross_structural_campaign_v1",
        "checkpoint_recertification_v1",
        "overlay_abstract_reuse_v1",
        "abstract_occurrence_accounting_v1",
        "abstract_stage_accounting_v1",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


def test_portable_replay_closes_two_structures_and_three_denominators(
    independent_cross_structural_campaign,
) -> None:
    campaign, _directory, result = independent_cross_structural_campaign
    document = result.to_document()
    assert document["campaign_preregistration_id"] == (
        campaign.preregistration.preregistration_id
    )
    assert document["campaign_closure_id"] == campaign.closure.closure_id
    assert document["registered_target_vertex_counts"] == [5, 6]
    assert document["registered_structural_context_count"] == 2
    assert document["closure_denominator"] == 2
    assert document["certificate_coverage_denominator"] == 2
    assert document["future_economics_cost_denominator"] == 2
    assert document["plan_certificate_count"] == 2
    assert document["noncertificate_count"] == 0
    assert document["historical_source_changed_row_count"] == 3
    assert document["historical_source_incremental_local_ground_draw_count"] == 12288
    assert document["fresh_ground_or_observer_event_count"] == 0
    assert len(set(document["ordered_source_overlay_ids"])) == 2
    assert len(set(document["ordered_quotient_model_ids"])) == 2
    assert document["cross_structural_model_transfer_attempted"] is False
    assert document["automatic_coordinate_primitive_invention_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["valid"] is True


def test_resigned_denominator_deletion_fails_before_child_replay(
    child_campaigns,
    cross_structural_campaign,
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign, directory = cross_structural_campaign
    copied = tmp_path / "aggregate"
    shutil.copytree(directory, copied)
    target = copied / "0004_CAMPAIGN_CLOSURE.json"
    document = loads_canonical_json(target.read_bytes())
    document["closure_denominator"] = 1
    document = _resign(
        document,
        "campaign_closure_id",
        CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN,
    )
    target.write_bytes(canonical_json_bytes(document))

    def forbidden(**_kwargs):
        raise AssertionError("cheap denominator gate called a child verifier")

    monkeypatch.setattr(
        verifier.w5_verifier_v1,
        "verify_heldout_abstract_campaign_directory_bytes_v1",
        forbidden,
    )
    monkeypatch.setattr(
        verifier.k6_verifier_v1,
        "verify_heldout_k6_abstract_campaign_directory_bytes_v1",
        forbidden,
    )
    with pytest.raises(
        verifier.ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error,
        match="denominator gate",
    ):
        verifier.verify_heldout_cross_structural_campaign_directory_bytes_v1(
            campaign_directory=copied,
            w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
            k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
            k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=document["campaign_closure_id"],
        )


def test_resigned_cross_model_row_is_rejected(
    child_campaigns,
    cross_structural_campaign,
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign, directory = cross_structural_campaign
    copied = tmp_path / "aggregate"
    shutil.copytree(directory, copied)
    w5_row = loads_canonical_json((copied / "0002_W5_CHILD_ROW.json").read_bytes())
    k6_target = copied / "0003_K6_CHILD_ROW.json"
    k6_row = loads_canonical_json(k6_target.read_bytes())
    k6_row["quotient_model_id"] = w5_row["quotient_model_id"]
    k6_row = _resign(
        k6_row,
        "cross_structural_child_row_id",
        CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CHILD_ROW_V1_DOMAIN,
    )
    k6_target.write_bytes(canonical_json_bytes(k6_row))
    closure_target = copied / "0004_CAMPAIGN_CLOSURE.json"
    closure = loads_canonical_json(closure_target.read_bytes())
    closure["ordered_child_row_ids"][1] = k6_row["cross_structural_child_row_id"]
    closure = _resign(
        closure,
        "campaign_closure_id",
        CONSTRUCTION_K7_HELDOUT_CROSS_STRUCTURAL_CAMPAIGN_CLOSURE_V1_DOMAIN,
    )
    closure_target.write_bytes(canonical_json_bytes(closure))
    w5_value, k6_value = _cached_child_verifications(campaign)
    monkeypatch.setattr(
        verifier.w5_verifier_v1,
        "verify_heldout_abstract_campaign_directory_bytes_v1",
        lambda **_kwargs: w5_value,
    )
    monkeypatch.setattr(
        verifier.k6_verifier_v1,
        "verify_heldout_k6_abstract_campaign_directory_bytes_v1",
        lambda **_kwargs: k6_value,
    )
    with pytest.raises(
        verifier.ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error,
        match="child row",
    ):
        verifier.verify_heldout_cross_structural_campaign_directory_bytes_v1(
            campaign_directory=copied,
            w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
            k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
            k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=closure["campaign_closure_id"],
        )


def test_missing_aggregate_row_is_rejected(
    child_campaigns,
    cross_structural_campaign,
    tmp_path: Path,
) -> None:
    campaign, directory = cross_structural_campaign
    copied = tmp_path / "aggregate"
    shutil.copytree(directory, copied)
    (copied / "0003_K6_CHILD_ROW.json").unlink()
    with pytest.raises(
        verifier.ConstructionK7HeldoutCrossStructuralCampaignIndependentVerifierV1Error,
        match="inventory",
    ):
        verifier.verify_heldout_cross_structural_campaign_directory_bytes_v1(
            campaign_directory=copied,
            w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
            k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
            k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=campaign.closure.closure_id,
        )
