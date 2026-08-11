from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_positive_promoted_campaign_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_positive_promoted_overlay_v1 import positive_promoted
from tests.test_v075_batched_causal_occurrence_successor_v1 import (
    positive_batched_occurrence,
)


@pytest.fixture(scope="module")
def positive_campaign(positive_promoted, tmp_path_factory):
    directory = tmp_path_factory.mktemp("positive-promoted-campaign") / "campaign"
    result = subject.run_positive_promoted_campaign_v1(
        positive_promoted[-1], campaign_directory=directory
    )
    return result, directory


def test_domains_and_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7PositivePromotedCampaignV1Error",
        "LOCAL_DOMAINS",
        "PositivePromotedCampaignClosureV1",
        "PositivePromotedCampaignFileCommitV1",
        "PositivePromotedCampaignOccurrenceRowV1",
        "PositivePromotedCampaignPreregistrationV1",
        "PositivePromotedCampaignResultV1",
        "run_positive_promoted_campaign_v1",
        "verify_positive_promoted_campaign_v1",
    }


def test_preregistered_occurrence_closes_all_three_denominators(
    positive_campaign,
) -> None:
    result, directory = positive_campaign
    verified = subject.verify_positive_promoted_campaign_v1(result)
    closure = verified.closure.to_document()
    assert closure["registered_logical_occurrence_count"] == 1
    assert closure["closed_logical_occurrence_count"] == 1
    assert closure["closure_denominator"] == 1
    assert closure["certificate_coverage_denominator"] == 1
    assert closure["future_economics_cost_denominator"] == 1
    assert closure["plan_certificate_count"] == 1
    assert closure["infeasibility_certificate_count"] == 0
    assert closure["noncertificate_count"] == 0
    assert closure["official_execution_allowed"] is False
    assert (directory / subject.OCCURRENCE_OUTPUT_DIRECTORY).is_dir()


def test_occurrence_row_retains_formal_abstract_certificate_chain(
    positive_campaign,
) -> None:
    result, _directory = positive_campaign
    row = result.occurrence_row.to_document()
    assert row["route_kind"] == "ABSTRACT_ONLY_CERTIFICATE"
    assert row["terminal_class"] == "PLAN_CERTIFICATE"
    assert row["terminal_code"] == "ABSTRACT_CERTIFIED"
    assert row["work_vector_id"] == result.occurrence_bundle.work_vector.work_vector_id
    assert row["comparison_vector_id"] == (
        result.occurrence_bundle.comparison_vector.comparison_vector_id
    )
    assert result.closure.cumulative_comparison_values == (
        result.occurrence_bundle.comparison_vector.values
    )


def test_three_campaign_files_match_durable_commit_receipts(
    positive_campaign,
) -> None:
    result, directory = positive_campaign
    assert tuple(row.filename for row in result.file_commits) == (
        subject.PREREGISTRATION_FILENAME,
        subject.OCCURRENCE_ROW_FILENAME,
        subject.CLOSURE_FILENAME,
    )
    for row in result.file_commits:
        raw = (directory / row.filename).read_bytes()
        assert len(raw) == row.byte_count
        assert hashlib.sha256(raw).hexdigest() == row.bytes_sha256
    assert result.preregistration.to_document()[
        "preregistration_committed_before_planner_execution"
    ] is True


def test_denominator_row_mutation_is_rejected(positive_campaign) -> None:
    result, _directory = positive_campaign
    original = result.occurrence_row.comparison_values
    changed = ((original[0][0], original[0][1] + 1), *original[1:])
    try:
        object.__setattr__(result.occurrence_row, "comparison_values", changed)
        with pytest.raises(subject.ConstructionK7PositivePromotedCampaignV1Error):
            subject.verify_positive_promoted_campaign_v1(result)
    finally:
        object.__setattr__(result.occurrence_row, "comparison_values", original)


def test_existing_campaign_directory_is_rejected(
    positive_promoted,
    tmp_path: Path,
) -> None:
    with pytest.raises(subject.ConstructionK7PositivePromotedCampaignV1Error):
        subject.run_positive_promoted_campaign_v1(
            positive_promoted[-1], campaign_directory=tmp_path
        )
