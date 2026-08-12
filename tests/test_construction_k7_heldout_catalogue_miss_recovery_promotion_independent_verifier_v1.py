from __future__ import annotations

import ast
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_heldout_catalogue_miss_recovery_promotion_independent_verifier_v1
    as subject,
)
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN,
    canonical_json_bytes,
    content_id,
    loads_canonical_json,
)
from tests.test_construction_k7_heldout_catalogue_miss_recovery_promotion_v1 import (
    promotion_campaign,
)
from tests.test_construction_k7_heldout_cross_structural_campaign_v1 import (
    child_campaigns,
)


def _copy_campaign(source: Path, target: Path) -> None:
    target.mkdir(mode=0o700)
    for filename in subject.EXPECTED_FILENAMES:
        (target / filename).write_bytes((source / filename).read_bytes())


def test_import_surface_is_producer_free() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    forbidden_exact = {
        "acfqp.construction_k7_heldout_catalogue_miss_recovery_promotion_v1",
        "acfqp.construction_k7_heldout_catalogue_query_router_v1",
        "acfqp.construction_k7_heldout_reusable_model_catalogue_v1",
        "acfqp.construction_k7_heldout_k6_checkpoint_recertification_v1",
        "acfqp.construction_k7_heldout_k6_overlay_abstract_reuse_v1",
    }
    assert not (imported & forbidden_exact)
    assert set(subject.__all__) == {
        "CataloguePromotionDirectoryVerificationV1",
        "ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error",
        "EXPECTED_FILENAMES",
        "verify_catalogue_promotion_campaign_directory_bytes_v1",
    }


def test_directory_replay_rebuilds_miss_recovery_promotion_and_fresh_plan(
    promotion_campaign,
) -> None:
    result, directory = promotion_campaign
    verification = subject.verify_catalogue_promotion_campaign_directory_bytes_v1(
        directory
    )
    document = verification.to_document()
    assert verification.preregistration_id == result.preregistration.preregistration_id
    assert verification.promotion_id == result.promotion.promotion_id
    assert verification.final_route_result_id == result.final_route.result_id
    assert verification.closure_id == result.closure.closure_id
    assert document["producer_import_count"] == 0
    assert document["initial_miss_independently_replayed"] is True
    assert document["k6_local_recovery_independently_replayed"] is True
    assert document["catalogue_epoch_promotion_independently_replayed"] is True
    assert document["fresh_postpromotion_abstract_plan_independently_replayed"] is True
    assert document["physical_campaign_bytes_verified"] is True
    assert document["valid"] is True


def test_resigned_denominator_deletion_is_rejected(
    promotion_campaign,
    tmp_path: Path,
) -> None:
    _result, source_directory = promotion_campaign
    directory = tmp_path / "campaign"
    _copy_campaign(source_directory, directory)
    target = directory / subject.CLOSURE_FILENAME
    document = loads_canonical_json(target.read_bytes())
    document["logical_occurrence_denominator"] = 0
    payload = {
        key: value
        for key, value in document.items()
        if key != "campaign_closure_id"
    }
    document["campaign_closure_id"] = content_id(
        CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_CLOSURE_V1_DOMAIN,
        payload,
    )
    target.write_bytes(canonical_json_bytes(document))
    with pytest.raises(
        subject.ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error,
        match="closure or denominator changed",
    ):
        subject.verify_catalogue_promotion_campaign_directory_bytes_v1(directory)


def test_resigned_promoted_entry_model_swap_is_rejected(
    promotion_campaign,
    tmp_path: Path,
) -> None:
    _result, source_directory = promotion_campaign
    directory = tmp_path / "campaign"
    _copy_campaign(source_directory, directory)
    target = directory / subject.PROMOTION_FILENAME
    document = loads_canonical_json(target.read_bytes())
    document["promoted_entry"]["quotient_model_id"] = "f" * 64
    payload = {
        key: value
        for key, value in document.items()
        if key not in {"model_promotion_id", "promoted_entry", "promoted_catalogue"}
    }
    document["model_promotion_id"] = content_id(
        subject.CONSTRUCTION_K7_HELDOUT_CATALOGUE_PROMOTION_EVENT_V1_DOMAIN,
        payload,
    )
    target.write_bytes(canonical_json_bytes(document))
    with pytest.raises(
        subject.ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error
    ):
        subject.verify_catalogue_promotion_campaign_directory_bytes_v1(directory)


def test_missing_or_noncanonical_artifact_is_rejected(
    promotion_campaign,
    tmp_path: Path,
) -> None:
    _result, source_directory = promotion_campaign
    missing = tmp_path / "missing"
    _copy_campaign(source_directory, missing)
    (missing / subject.FINAL_ROUTE_FILENAME).unlink()
    with pytest.raises(
        subject.ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error,
        match="absent",
    ):
        subject.verify_catalogue_promotion_campaign_directory_bytes_v1(missing)

    malformed = tmp_path / "malformed"
    _copy_campaign(source_directory, malformed)
    target = malformed / subject.PREREGISTRATION_FILENAME
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(
        subject.ConstructionK7HeldoutCataloguePromotionIndependentVerifierV1Error,
        match="canonical",
    ):
        subject.verify_catalogue_promotion_campaign_directory_bytes_v1(malformed)
