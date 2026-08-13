from __future__ import annotations

import os
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_accounted_campaign_v12 as campaign
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre


def test_predecessor_and_fresh_task_are_frozen_before_execution() -> None:
    predecessor = campaign._predecessor_verification_document()
    assert predecessor["v169_independent_verification"][
        "independent_verification_id"
    ] == campaign.PREDECESSOR_VERIFICATION_ID
    assert predecessor["v169_campaign_canonical_byte_count"] == 431255
    assert predecessor["v169_campaign_canonical_sha256"] == (
        "d23ae1212c073343ee63395c759bec7dfb08a65e8734f88c66ec137253238ee9"
    )
    task = campaign._task_document(0, 1)
    assert task["accounted_preregistration_id"] == pre.PREREGISTRATION_ID
    assert task["evaluation_lane_separate_from_operational_route"] is True


def test_one_decision_smoke_closes_worker_route_and_campaign_vectors(
    tmp_path: Path,
) -> None:
    output = tmp_path / "accounted-smoke"
    document, chains = campaign._materialize_campaign(
        output_root=output,
        decision_limit=1,
        episode_count=1,
    )
    assert document["accounted_campaign_id"] == (
        "28e0f5dd02157094d02c3ffd0df523a157dc10ef66c6afadc85e476e8da31bd1"
    )
    assert document["episode_count"] == 1
    assert document["decision_count"] == 1
    assert document["abstract_route_count"] == 0
    assert document["fallback_route_count"] == 1
    assert document["operational_work_vector_count"] == 4
    assert document["evaluation_work_vector_count"] == 0
    assert len(chains) == 4
    assert len(document["vector_prefix_totals"]) == 4
    assert document["all_nine_shared_resource_paths_closed"] is True
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["official_scalar_cost"] is None
    assert sum(1 for path in output.rglob("*") if path.is_file()) == 24
    final = {
        row["axis"]: row["value"]
        for row in document["final_operational_comparison_totals"]
    }
    assert final["kernel_transition_calls"] > 0
    assert final["nonkernel_compute_events"] > 0
    assert final["process_launches"] == 1
    assert final["output_bytes"] > 0


@pytest.mark.skipif(
    os.environ.get("ACFQP_RUN_ACCOUNTED_2048") != "1",
    reason="the full four-episode accounted campaign is intentionally explicit",
)
def test_full_preregistered_accounted_campaign(tmp_path: Path) -> None:
    result = campaign.run_standard_2048_accounted_campaign_v12(
        output_root=tmp_path / "full-accounted-campaign"
    )
    document = result.to_document()
    assert document["episode_count"] == 4
    assert document["decision_count"] <= 256
    assert document["all_nine_shared_resource_paths_closed"] is True
    assert document["all_selected_actions_exact_value_and_loss_equivalent"] is True
    assert document["independent_complete_bundle_verifier_present"] is False
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
