from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_expression_full_accounted_campaign_v34 as campaign
from acfqp.phase3e_ids import canonical_json_bytes, loads_canonical_json


def test_checkpoint_plan_reconstructs_every_registered_segment() -> None:
    specs = campaign._checkpoint_specs()
    assert [row.profile for row in specs] == [
        "V26",
        "V27",
        "V28",
        "V29",
        "V30",
        "V31",
        "V32",
        "V33",
    ]
    assert [row.expected_new_decision_count for row in specs] == [
        128,
        128,
        128,
        256,
        512,
        938,
        765,
        204,
    ]
    assert sum(row.expected_new_decision_count for row in specs) + 128 == 3187
    assert specs[-2].statuses == ("ACTIVE", "LOST", "ACTIVE", "ACTIVE")
    assert specs[-1].statuses == ("ACTIVE", "LOST", "LOST", "ACTIVE")


def test_terminal_checkpoint_carries_identity_with_zero_route_work() -> None:
    specs = {row.profile: row for row in campaign._checkpoint_specs()}
    episode, operational, evaluation, checkpoints = campaign._checkpoint_episode(
        specs["V33"], 1
    )
    assert episode["expression_checkpoint_episode_id"] == campaign.FINAL_EPISODE_IDS[1]
    assert episode["segment_decision_count"] == 0
    assert episode["closure_reason"] == "TERMINAL_STATE"
    assert not any(operational.values())
    assert not any(evaluation.values())
    assert checkpoints == 0


def test_worker_rejects_crossed_source_episode_identity() -> None:
    spec = {row.profile: row for row in campaign._checkpoint_specs()}["V33"]
    raw = campaign._task_document(
        profile="V33", episode_index=1, source_episode_id=spec.source_episode_ids[1]
    )
    forged = loads_canonical_json(raw)
    assert type(forged) is dict
    forged["source_episode_id"] = "f" * 64
    payload = {
        key: value
        for key, value in forged.items()
        if key != "expression_full_accounting_measurement_id"
    }
    from acfqp.phase3e_ids import content_id

    forged["expression_full_accounting_measurement_id"] = content_id(
        campaign.pre.FUTURE_DOMAINS["measurement"], payload
    )
    with pytest.raises(
        campaign.ConstructionK7Standard2048ExpressionFullAccountedCampaignV34Error
    ):
        campaign._worker(canonical_json_bytes(forged))


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_FULL_2048_ACCOUNTING") != "1",
    reason="requires the preregistered multi-segment exact accounting run",
)
def test_full_accounted_campaign_materializes_all_native_windows(
    tmp_path: Path,
) -> None:
    result = campaign.run_standard_2048_expression_full_accounted_campaign_v34(
        tmp_path / "full-accounting"
    )
    document = result.to_document()
    assert document["segment_count"] == 9
    assert document["complete_decision_count"] == 3187
    assert document["won_occurrence_count"] == 2
    assert document["lost_occurrence_count"] == 2
    assert document["all_3187_decisions_rerun_under_native_counter_windows"] is True
    assert document["all_nine_shared_resource_paths_have_measurement_receipts"] is True
    assert document["summary_to_counter_translation_used"] is False
    assert document["official_execution_allowed"] is False
