from __future__ import annotations

import ast
from pathlib import Path
import os
import subprocess
import sys

import pytest

from acfqp import construction_k7_heldout_cross_structural_campaign_v1 as subject
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS, loads_canonical_json


@pytest.fixture(scope="session")
def child_campaigns(tmp_path_factory):
    root = tmp_path_factory.mktemp("heldout-cross-structural-children")
    helper = Path(__file__).with_name("_heldout_cross_structural_campaign_worker.py")
    environment = dict(os.environ)
    environment["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    processes = []
    for family in ("W5", "K6"):
        output = root / family.lower()
        process = subprocess.Popen(
            [sys.executable, str(helper), family, str(output)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=environment,
        )
        processes.append((family, output, process))
    results = {}
    for family, output, process in processes:
        stdout, stderr = process.communicate(timeout=900)
        assert process.returncode == 0, (family, stdout, stderr)
        manifest = loads_canonical_json((output / "manifest.json").read_bytes())
        results[family] = {
            "reuse_bytes": (output / "reuse-result.json").read_bytes(),
            "campaign_directory": output / manifest["campaign_directory"],
            "preregistration_id": manifest["campaign_preregistration_id"],
            "closure_id": manifest["campaign_closure_id"],
        }
    return results


@pytest.fixture(scope="module")
def cross_structural_campaign(child_campaigns, tmp_path_factory):
    directory = (
        tmp_path_factory.mktemp("heldout-cross-structural-campaign") / "campaign"
    )
    result = subject.run_heldout_cross_structural_campaign_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
        k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
        campaign_directory=directory,
    )
    return result, directory


def test_domains_surface_and_imports_are_additive() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "ConstructionK7HeldoutCrossStructuralCampaignV1Error",
        "EXPECTED_FILENAMES",
        "HeldoutCrossStructuralCampaignChildRowV1",
        "HeldoutCrossStructuralCampaignClosureV1",
        "HeldoutCrossStructuralCampaignFileCommitV1",
        "HeldoutCrossStructuralCampaignPreregistrationV1",
        "HeldoutCrossStructuralCampaignResultV1",
        "HeldoutCrossStructuralChildSpecV1",
        "LOCAL_DOMAINS",
        "run_heldout_cross_structural_campaign_v1",
        "verify_heldout_cross_structural_campaign_v1",
    }
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module
    }
    assert not any("checkpoint_recertification" in name for name in imported)
    assert not any("overlay_abstract_reuse_v1" in name for name in imported)
    assert not any("abstract_campaign_v1" in name for name in imported)


def test_two_structures_close_without_cross_model_transfer(
    cross_structural_campaign,
) -> None:
    result, _directory = cross_structural_campaign
    verified = subject.verify_heldout_cross_structural_campaign_v1(result)
    closure = verified.closure.to_document()
    assert [row.spec.family_key for row in verified.rows] == ["W5", "K6"]
    assert [row.spec.target_vertex_count for row in verified.rows] == [5, 6]
    assert len({row.source_overlay_id for row in verified.rows}) == 2
    assert len({row.quotient_model_id for row in verified.rows}) == 2
    assert len({row.query_id for row in verified.rows}) == 2
    assert closure["closure_denominator"] == 2
    assert closure["certificate_coverage_denominator"] == 2
    assert closure["future_economics_cost_denominator"] == 2
    assert closure["plan_certificate_count"] == 2
    assert closure["noncertificate_count"] == 0
    assert closure["historical_source_changed_row_count"] == 3
    assert closure["historical_source_incremental_local_ground_draw_count"] == 12288
    assert closure["fresh_ground_or_observer_event_count"] == 0
    assert closure["cross_structural_model_transfer_attempted"] is False


def test_cumulative_vector_is_exact_child_sum(cross_structural_campaign) -> None:
    result, _directory = cross_structural_campaign
    rows = result.rows
    expected = tuple(
        (
            axis,
            dict(rows[0].comparison_values)[axis]
            + dict(rows[1].comparison_values)[axis],
        )
        for axis in dict(rows[0].comparison_values)
    )
    assert result.closure.cumulative_comparison_values == expected
    assert all(
        row.to_document()["route_kind"] == "ABSTRACT_ONLY_CERTIFICATE"
        and row.to_document()["fresh_ground_or_observer_event_count"] == 0
        for row in rows
    )


def test_preregistration_precedes_both_independent_replays(
    child_campaigns,
    cross_structural_campaign,
    tmp_path: Path,
    monkeypatch,
) -> None:
    output = tmp_path / "campaign"
    observed = []
    prior, _prior_directory = cross_structural_campaign
    w5_document = loads_canonical_json(prior.rows[0].child_verification_bytes)
    k6_document = loads_canonical_json(prior.rows[1].child_verification_bytes)
    w5_verification = subject.w5_verifier_v1.HeldoutAbstractCampaignDirectoryVerificationV1(
        w5_document["heldout_overlay_abstract_reuse_independent_verification_id"],
        w5_document["campaign_preregistration_id"],
        w5_document["occurrence_accounting_bundle_id"],
        w5_document["campaign_occurrence_row_id"],
        w5_document["campaign_closure_id"],
        w5_document["work_vector_id"],
        w5_document["comparison_vector_id"],
        w5_document["io.output_bytes"],
        tuple(
            (row["axis"], row["value"])
            for row in w5_document["comparison_values"]
        ),
    )
    k6_verification = subject.k6_verifier_v1.HeldoutK6AbstractCampaignDirectoryVerificationV1(
        k6_document["heldout_k6_overlay_abstract_reuse_independent_verification_id"],
        k6_document["campaign_preregistration_id"],
        k6_document["occurrence_accounting_bundle_id"],
        k6_document["campaign_occurrence_row_id"],
        k6_document["campaign_closure_id"],
        k6_document["work_vector_id"],
        k6_document["comparison_vector_id"],
        k6_document["io.output_bytes"],
        tuple(
            (row["axis"], row["value"])
            for row in k6_document["comparison_values"]
        ),
    )

    def wrapped_w5(**kwargs):
        observed.append(("W5", (output / subject.PREREGISTRATION_FILENAME).is_file()))
        return w5_verification

    def wrapped_k6(**kwargs):
        observed.append(("K6", (output / subject.PREREGISTRATION_FILENAME).is_file()))
        return k6_verification

    monkeypatch.setattr(
        subject.w5_verifier_v1,
        "verify_heldout_abstract_campaign_directory_bytes_v1",
        wrapped_w5,
    )
    monkeypatch.setattr(
        subject.k6_verifier_v1,
        "verify_heldout_k6_abstract_campaign_directory_bytes_v1",
        wrapped_k6,
    )
    subject.run_heldout_cross_structural_campaign_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
        k6_reuse_result_bytes=child_campaigns["K6"]["reuse_bytes"],
        k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
        campaign_directory=output,
    )
    assert observed == [("W5", True), ("K6", True)]


def test_crossed_family_bytes_are_rejected_before_replay(
    child_campaigns,
    tmp_path: Path,
    monkeypatch,
) -> None:
    def forbidden(**_kwargs):
        raise AssertionError("child verifier must not run for crossed family bytes")

    monkeypatch.setattr(
        subject.w5_verifier_v1,
        "verify_heldout_abstract_campaign_directory_bytes_v1",
        forbidden,
    )
    with pytest.raises(
        subject.ConstructionK7HeldoutCrossStructuralCampaignV1Error,
        match="K6 reuse result schema",
    ):
        subject.run_heldout_cross_structural_campaign_v1(
            w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            w5_campaign_directory=child_campaigns["W5"]["campaign_directory"],
            k6_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
            k6_campaign_directory=child_campaigns["K6"]["campaign_directory"],
            campaign_directory=tmp_path / "campaign",
        )


def test_commits_and_official_claim_boundaries_remain_locked(
    cross_structural_campaign,
) -> None:
    result, directory = cross_structural_campaign
    assert tuple(row.filename for row in result.file_commits) == subject.EXPECTED_FILENAMES
    for commit in result.file_commits:
        raw = (directory / commit.filename).read_bytes()
        assert len(raw) == commit.byte_count
        assert __import__("hashlib").sha256(raw).hexdigest() == commit.bytes_sha256
    closure = result.closure.to_document()
    assert closure["automatic_coordinate_primitive_invention_claimed"] is False
    assert closure["broad_cross_domain_generalization_claimed"] is False
    assert closure["campaign_orchestration_work_vector_issued"] is False
    assert closure["official_execution_allowed"] is False
    assert closure["official_scalar_cost"] is None
    assert closure["official_N_break_even"] is None


def test_row_deletion_cannot_be_reclassified_as_one_occurrence(
    cross_structural_campaign,
) -> None:
    result, _directory = cross_structural_campaign
    original = result.closure.rows
    try:
        object.__setattr__(result.closure, "rows", original[:1])
        with pytest.raises(subject.ConstructionK7HeldoutCrossStructuralCampaignV1Error):
            subject.verify_heldout_cross_structural_campaign_v1(result)
    finally:
        object.__setattr__(result.closure, "rows", original)
