from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_heldout_k6_abstract_campaign_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_heldout_k6_overlay_abstract_reuse_v1 import (
    fresh_results,
)


@pytest.fixture(scope="module")
def heldout_k6_campaign(fresh_results, tmp_path_factory):
    directory = tmp_path_factory.mktemp("heldout-k6-abstract-campaign") / "campaign"
    result = subject.run_heldout_k6_abstract_campaign_v1(
        fresh_results[1], campaign_directory=directory
    )
    return result, directory


def test_domains_and_surface_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutK6AbstractCampaignV1Error",
        "LOCAL_DOMAINS",
        "HeldoutK6AbstractCampaignClosureV1",
        "HeldoutK6AbstractCampaignFileCommitV1",
        "HeldoutK6AbstractCampaignOccurrenceRowV1",
        "HeldoutK6AbstractCampaignPreregistrationV1",
        "HeldoutK6AbstractCampaignResultV1",
        "run_heldout_k6_abstract_campaign_v1",
        "verify_heldout_k6_abstract_campaign_v1",
    }


def test_preregistered_k6_occurrence_closes_all_denominators(
    heldout_k6_campaign,
) -> None:
    result, directory = heldout_k6_campaign
    verified = subject.verify_heldout_k6_abstract_campaign_v1(result)
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


def test_occurrence_row_retains_formal_k6_abstract_chain(
    heldout_k6_campaign,
) -> None:
    result, _directory = heldout_k6_campaign
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
    heldout_k6_campaign,
) -> None:
    result, directory = heldout_k6_campaign
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
        "preregistration_committed_before_accounting_execution"
    ] is True


def test_campaign_keeps_gates_and_scalar_locked(heldout_k6_campaign) -> None:
    result, _directory = heldout_k6_campaign
    closure = result.closure.to_document()
    assert closure["campaign_construction_closed"] is True
    assert closure["official_certificate_coverage_authority"] is False
    assert closure["counter_completeness_gate_status"] == (
        "COUNTER_COMPLETENESS_GATE_NOT_RUN"
    )
    assert closure["workload_economics_gate_status"] == (
        "WORKLOAD_ECONOMICS_GATE_NOT_RUN"
    )
    assert closure["official_scalar_cost"] is None
    assert closure["official_N_break_even"] is None


def test_denominator_mutation_is_rejected(heldout_k6_campaign) -> None:
    result, _directory = heldout_k6_campaign
    original = result.occurrence_row.comparison_values
    changed = ((original[0][0], original[0][1] + 1), *original[1:])
    try:
        object.__setattr__(result.occurrence_row, "comparison_values", changed)
        with pytest.raises(subject.ConstructionK7HeldoutK6AbstractCampaignV1Error):
            subject.verify_heldout_k6_abstract_campaign_v1(result)
    finally:
        object.__setattr__(result.occurrence_row, "comparison_values", original)


def test_existing_campaign_directory_is_rejected(
    fresh_results,
    tmp_path: Path,
) -> None:
    with pytest.raises(subject.ConstructionK7HeldoutK6AbstractCampaignV1Error):
        subject.run_heldout_k6_abstract_campaign_v1(
            fresh_results[1], campaign_directory=tmp_path
        )
