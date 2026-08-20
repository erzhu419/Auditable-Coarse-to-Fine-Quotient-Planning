import pytest

from acfqp.construction_k7_bounded_source_campaign_v82 import (
    ConstructionK7BoundedSourceCampaignV82Error,
    freeze_bounded_source_failure_v82,
    run_bounded_source_campaign_v82,
    verify_bounded_source_campaign_v82,
)


def test_v82_campaign_rejects_foreign_values():
    with pytest.raises(ConstructionK7BoundedSourceCampaignV82Error):
        verify_bounded_source_campaign_v82(object())


def test_v82_preserves_terminal_frontier_compilation_failure():
    document = freeze_bounded_source_failure_v82().to_document()
    assert document["failure_phase"] == (
        "TERMINAL_FRONTIER_COMPILATION_EXACTNESS_CHECK"
    )
    assert document["all_preregistered_source_member_processes_completed"] is True
    assert document["campaign_document_emitted"] is False
    assert document["fresh_target_outcome_count"] == 0
    assert document["same_identity_rerun_forbidden"] is True
    assert document["official_scalar_cost"] is None


def test_v82_same_identity_cannot_be_rerun():
    with pytest.raises(
        ConstructionK7BoundedSourceCampaignV82Error,
        match="same identity will not be rerun",
    ):
        run_bounded_source_campaign_v82()
