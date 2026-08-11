from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import shutil

import pytest

from acfqp import (
    construction_k7_heldout_abstract_campaign_independent_verifier_v1 as verifier,
)
from acfqp import construction_k7_heldout_abstract_campaign_v1 as campaign_v1
from acfqp import construction_k7_heldout_checkpoint_recertification_v1 as source_v1
from acfqp import construction_k7_heldout_overlay_abstract_reuse_v1 as reuse_v1
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)


def _id(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


@pytest.fixture(scope="module")
def heldout_campaign(tmp_path_factory):
    source = source_v1.run_heldout_checkpoint_recertification_v1()
    reuse = reuse_v1.run_heldout_overlay_abstract_reuse_v1(
        source,
        logical_occurrence_id=_id("heldout-independent-campaign-occurrence-v1"),
        occurrence_ordinal=4,
    )
    directory = tmp_path_factory.mktemp("heldout-independent-campaign") / "campaign"
    return (
        campaign_v1.run_heldout_abstract_campaign_v1(
            reuse, campaign_directory=directory
        ),
        directory,
    )


def test_independent_surface_and_import_boundary_are_narrow() -> None:
    assert verifier.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(verifier.LOCAL_DOMAINS) == 1
    assert set(verifier.__all__) == {
        "ConstructionK7HeldoutAbstractCampaignIndependentVerifierV1Error",
        "LOCAL_DOMAINS",
        "HeldoutAbstractCampaignDirectoryVerificationV1",
        "verify_heldout_abstract_campaign_directory_bytes_v1",
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
        "construction_k7_heldout_abstract_campaign_v1",
        "construction_k7_heldout_abstract_occurrence_accounting_v1",
        "construction_k7_heldout_abstract_stage_accounting_v1",
        "construction_k7_heldout_overlay_abstract_reuse_v1",
        "construction_k7_heldout_checkpoint_recertification_v1",
    )
    assert not any(any(name in item for name in forbidden) for item in imported)


@pytest.fixture(scope="module")
def independent_campaign(heldout_campaign):
    campaign, directory = heldout_campaign
    result = verifier.verify_heldout_abstract_campaign_directory_bytes_v1(
        reuse_result_bytes=canonical_json_bytes(campaign.reuse_result.to_document()),
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
    assert document["work_vector_id"] == (
        campaign.occurrence_bundle.work_vector.work_vector_id
    )
    assert document["comparison_vector_id"] == (
        campaign.occurrence_bundle.comparison_vector.comparison_vector_id
    )
    assert document["io.output_bytes"] == (
        campaign.occurrence_bundle.fixed_point.output_bytes
    )
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
    assert values["common.protocol_checks"] == 6
    assert values["io.staged_bytes"] == 0
    assert values["process.launches"] == 0
    assert result.comparison_values == (
        campaign.occurrence_bundle.comparison_vector.values
    )
    assert all(
        value == 0
        for path, value in values.items()
        if path.startswith(("local.", "fallback.", "rebuild."))
    )


def test_resigned_denominator_deletion_is_rejected_before_reuse_replay(
    heldout_campaign,
    tmp_path: Path,
    monkeypatch,
) -> None:
    campaign, directory = heldout_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    target = copied / "0003_CAMPAIGN_CLOSURE.json"
    document = loads_canonical_json(target.read_bytes())
    document["closure_denominator"] = 0
    payload = dict(document)
    payload.pop("campaign_closure_id")
    document["campaign_closure_id"] = content_id(
        CONSTRUCTION_K7_HELDOUT_ABSTRACT_CAMPAIGN_CLOSURE_V1_DOMAIN,
        payload,
    )
    target.write_bytes(canonical_json_bytes(document))

    def forbidden(*_args, **_kwargs):
        raise AssertionError("denominator gate ran expensive reuse replay")

    monkeypatch.setattr(
        verifier.reuse_verifier_v1,
        "verify_heldout_overlay_abstract_reuse_bytes_v1",
        forbidden,
    )
    with pytest.raises(
        verifier.ConstructionK7HeldoutAbstractCampaignIndependentVerifierV1Error,
        match="denominator gate",
    ):
        verifier.verify_heldout_abstract_campaign_directory_bytes_v1(
            reuse_result_bytes=canonical_json_bytes(
                campaign.reuse_result.to_document()
            ),
            campaign_directory=copied,
            expected_preregistration_id=campaign.preregistration.preregistration_id,
            expected_closure_id=campaign.closure.closure_id,
        )


def test_missing_occurrence_role_is_rejected(
    heldout_campaign, tmp_path: Path
) -> None:
    _campaign, directory = heldout_campaign
    copied = tmp_path / "campaign"
    shutil.copytree(directory, copied)
    (copied / "occurrence-0001" / "WORK_VECTOR.json").unlink()
    with pytest.raises(
        verifier.ConstructionK7HeldoutAbstractCampaignIndependentVerifierV1Error
    ):
        verifier.verify_heldout_abstract_campaign_directory_bytes_v1(
            reuse_result_bytes=b"{}",
            campaign_directory=copied,
            expected_preregistration_id="0" * 64,
            expected_closure_id="0" * 64,
        )
