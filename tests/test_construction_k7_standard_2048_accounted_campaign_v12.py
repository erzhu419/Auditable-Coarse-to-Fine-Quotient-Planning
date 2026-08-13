from __future__ import annotations

import ast
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_accounted_campaign_v12 as campaign
from acfqp import (
    construction_k7_standard_2048_accounted_independent_verifier_v12 as independent,
)
from acfqp import construction_k7_standard_2048_accounted_preregistration_v12 as pre
from acfqp.phase3e_ids import canonical_json_bytes


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


def test_accounting_verifier_has_no_producer_import() -> None:
    source = Path(independent.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    forbidden = {
        "acfqp.construction_k7_standard_2048_accounted_campaign_v12",
        "acfqp.construction_k7_standard_2048_accounted_artifacts_v12",
        "acfqp.construction_k7_standard_2048_instrumented_runtime_v12",
    }
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert imported.isdisjoint(forbidden)
    with pytest.raises(
        independent.ConstructionK7Standard2048AccountedIndependentVerifierV12Error
    ):
        independent._object(b"{}\n", "noncanonical attack")


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
        "e3e25b8f7e931efece856b59d5261a0a6140c8dda7c3c9cb26976689552fa3c3"
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
    verification = independent.verify_standard_2048_accounted_campaign_bundle_independently_v12(
        campaign_bytes=canonical_json_bytes(document),
        output_root=output,
    )
    assert verification.verification_id == (
        "7be3fea230495add2f6c9f7ed5a1359eff64a75635e90341452b3877fadbf672"
    )
    assert verification.operational_work_vector_count == 4
    assert verification.evaluation_work_vector_count == 0
    attacked = output / "episode-0000" / "decision-0000" / "common" / "WORK_VECTOR.json"
    attacked.chmod(0o600)
    attacked.write_bytes(attacked.read_bytes() + b"\n")
    with pytest.raises(
        independent.ConstructionK7Standard2048AccountedIndependentVerifierV12Error
    ):
        independent.verify_standard_2048_accounted_campaign_bundle_independently_v12(
            campaign_bytes=canonical_json_bytes(document),
            output_root=output,
        )


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
