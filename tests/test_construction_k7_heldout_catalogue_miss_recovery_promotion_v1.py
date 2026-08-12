from __future__ import annotations

import ast
import hashlib
from pathlib import Path

import pytest

from acfqp import (
    construction_k7_heldout_catalogue_miss_recovery_promotion_v1 as subject,
)
from acfqp import partial_support_robust_planner_v1 as robust
from acfqp.phase3e_ids import PHASE3E_DOMAIN_TAGS
from tests.test_construction_k7_heldout_cross_structural_campaign_v1 import (
    child_campaigns,
)


@pytest.fixture(scope="session")
def promotion_campaign(child_campaigns, tmp_path_factory):
    directory = tmp_path_factory.mktemp("catalogue-miss-promotion") / "campaign"
    result = subject.run_catalogue_miss_recovery_promotion_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        campaign_directory=directory,
    )
    return result, directory


def test_domains_surface_and_no_prebuilt_k6_input() -> None:
    assert subject.LOCAL_DOMAINS <= PHASE3E_DOMAIN_TAGS
    assert len(subject.LOCAL_DOMAINS) == 4
    assert set(subject.__all__) == {
        "CatalogueModelPromotionEventV1",
        "CataloguePromotionCampaignClosureV1",
        "CataloguePromotionCampaignResultV1",
        "CataloguePromotionFileCommitV1",
        "CataloguePromotionPreregistrationV1",
        "ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error",
        "EXPECTED_FILENAMES",
        "LOCAL_DOMAINS",
        "run_catalogue_miss_recovery_promotion_v1",
        "verify_catalogue_miss_recovery_promotion_v1",
    }
    signature = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    runner = next(
        node
        for node in ast.walk(signature)
        if isinstance(node, ast.FunctionDef)
        and node.name == "run_catalogue_miss_recovery_promotion_v1"
    )
    argument_names = {
        item.arg for item in (*runner.args.args, *runner.args.kwonlyargs)
    }
    assert argument_names == {"w5_reuse_result_bytes", "campaign_directory"}


def test_miss_precedes_local_construction_and_entry_promotion(
    promotion_campaign,
) -> None:
    result, _directory = promotion_campaign
    preregistration = result.preregistration.to_document()
    promotion = result.promotion.to_document()
    assert preregistration["initial_model_count"] == 1
    assert preregistration["initial_miss"]["routing_outcome"] == "CONSTRUCTION_REQUIRED"
    assert preregistration["initial_miss"]["abstract_planner_invocations"] == 0
    assert preregistration["initial_miss"]["ground_draw_count"] == 0
    assert preregistration["construction_must_follow_preregistration_commit"] is True
    assert promotion["source_base_audit_status"] == "FAILED_PROOF_FRONTIER"
    assert promotion["source_final_audit_status"] == "CERTIFIED"
    assert promotion["source_changed_row_count"] == 1
    assert promotion["source_preserved_row_count"] == 19
    assert promotion["source_incremental_local_ground_draw_count"] == 8_192
    assert promotion["source_full_16384_row_closure_built"] is False
    assert promotion["local_ground_triggered_only_by_failed_certificate"] is True
    assert promotion["immutable_query_neutral_overlay_promoted"] is True
    assert result.source.base_audit.status is robust.RobustAuditStatus.FAILED_PROOF_FRONTIER
    assert result.source.overlay.audit.status is robust.RobustAuditStatus.CERTIFIED


def test_old_snapshot_remains_a_miss_and_new_snapshot_routes_abstractly(
    promotion_campaign,
) -> None:
    result, _directory = promotion_campaign
    assert tuple(
        item.family_key for item in result.preregistration.initial_catalogue.entries
    ) == ("W5",)
    assert result.preregistration.initial_miss.selection.outcome == "MODEL_MISS"
    assert tuple(item.family_key for item in result.promotion.promoted_catalogue.entries) == (
        "W5",
        "K6",
    )
    assert (
        result.preregistration.initial_catalogue.catalogue_id
        != result.promotion.promoted_catalogue.catalogue_id
    )
    assert result.final_route.selection.outcome == "EXACT_MODEL_MATCH"
    assert result.final_route.plan is not None
    assert result.final_route.plan.entry == result.promotion.promoted_entry
    assert result.final_route.to_document()["routing_outcome"] == "ABSTRACT_PLAN_CERTIFIED"


def test_postpromotion_query_is_one_abstract_plan_and_zero_fresh_ground(
    promotion_campaign,
) -> None:
    result, _directory = promotion_campaign
    route = result.final_route.to_document()
    closure = result.closure.to_document()
    assert route["abstract_planner_invocations"] == 1
    assert route["model_construction_invocations"] == 0
    assert route["observer_call_count"] == 0
    assert route["ground_draw_count"] == 0
    assert route["ground_solver_invocations"] == 0
    assert closure["logical_occurrence_denominator"] == 1
    assert closure["certificate_coverage_denominator"] == 1
    assert closure["future_economics_cost_denominator"] == 1
    assert closure["plan_certificate_count"] == 1
    assert closure["noncertificate_count"] == 0
    assert closure["historical_local_ground_draw_count"] == 8_192
    assert closure["fresh_postpromotion_ground_draw_count"] == 0
    assert closure["multi_step_plan_mainly_completed_in_reusable_abstract_model"] is True
    assert closure["ground_distinctions_restored_only_after_certificate_failure"] is True


def test_preregistration_is_physically_committed_before_source_builder(
    promotion_campaign,
    child_campaigns,
    tmp_path: Path,
    monkeypatch,
) -> None:
    prior, _prior_directory = promotion_campaign
    directory = tmp_path / "campaign"
    called = 0

    def reused_source():
        nonlocal called
        called += 1
        target = directory / subject.PREREGISTRATION_FILENAME
        assert target.is_file()
        assert target.read_bytes()
        return prior.source

    monkeypatch.setattr(
        subject.source_v1,
        "run_heldout_k6_checkpoint_recertification_v1",
        reused_source,
    )
    replay = subject.run_catalogue_miss_recovery_promotion_v1(
        w5_reuse_result_bytes=child_campaigns["W5"]["reuse_bytes"],
        campaign_directory=directory,
    )
    assert called == 1
    assert replay.preregistration.preregistration_id == prior.preregistration.preregistration_id
    assert replay.promotion.promotion_id == prior.promotion.promotion_id


def test_five_artifacts_are_exactly_committed_and_owner_graph_verifies(
    promotion_campaign,
) -> None:
    result, directory = promotion_campaign
    assert tuple(item.filename for item in result.file_commits) == subject.EXPECTED_FILENAMES
    for commit in result.file_commits:
        raw = (directory / commit.filename).read_bytes()
        assert len(raw) == commit.byte_count
        assert hashlib.sha256(raw).hexdigest() == commit.bytes_sha256
    subject.verify_catalogue_miss_recovery_promotion_v1(
        result,
        campaign_directory=directory,
    )


def test_file_tamper_and_catalogue_parent_mutation_are_rejected(
    promotion_campaign,
    tmp_path: Path,
) -> None:
    result, directory = promotion_campaign
    copied = tmp_path / "campaign"
    copied.mkdir(mode=0o700)
    for commit in result.file_commits:
        (copied / commit.filename).write_bytes((directory / commit.filename).read_bytes())
    target = copied / subject.PROMOTION_FILENAME
    target.write_bytes(target.read_bytes() + b"\n")
    with pytest.raises(
        subject.ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error,
        match="artifact bytes changed",
    ):
        subject.verify_catalogue_miss_recovery_promotion_v1(
            result,
            campaign_directory=copied,
        )

    original = result.promotion.promoted_catalogue
    try:
        object.__setattr__(
            result.promotion,
            "promoted_catalogue",
            result.preregistration.initial_catalogue,
        )
        with pytest.raises(
            subject.ConstructionK7HeldoutCatalogueMissRecoveryPromotionV1Error
        ):
            result.promotion.promotion_id
    finally:
        object.__setattr__(result.promotion, "promoted_catalogue", original)


def test_claim_boundaries_remain_locked(promotion_campaign) -> None:
    result, _directory = promotion_campaign
    promotion = result.promotion.to_document()
    closure = result.closure.to_document()
    assert promotion["automatic_coordinate_primitive_invention_claimed"] is False
    assert closure["broad_cross_domain_generalization_claimed"] is False
    assert closure["official_execution_allowed"] is False
    assert closure["official_scalar_cost"] is None
    assert closure["official_N_break_even"] is None
    assert closure["counter_completeness_gate_status"] == "NOT_RUN"
    assert closure["workload_economics_gate_status"] == "NOT_RUN"

