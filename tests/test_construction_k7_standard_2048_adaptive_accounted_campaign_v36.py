from __future__ import annotations

import copy
import os
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_adaptive_accounted_campaign_v36 as campaign
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FULL = os.environ.get("ACFQP_RUN_ADAPTIVE_ACCOUNTING_V36") == "1"
V35_CAMPAIGN_PATH = Path(
    os.environ.get(
        "ACFQP_V35_CAMPAIGN_PATH",
        "/tmp/acfqp-v35-adaptive-expression-campaign.canonical.json",
    )
)
V35_VERIFICATION_PATH = Path(
    os.environ.get(
        "ACFQP_V35_VERIFICATION_PATH",
        "/tmp/acfqp-v35-adaptive-expression-verification.canonical.json",
    )
)
V36_OUTPUT_ROOT = Path(
    os.environ.get(
        "ACFQP_V36_OUTPUT_ROOT", "/tmp/acfqp-v36-adaptive-accounting"
    )
)


def test_v35_gate_fails_before_output_or_target_access(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    if campaign.V35_CAMPAIGN_ID != "0" * 64:
        pytest.skip("V35 predecessor is now frozen")
    output = tmp_path / "must-not-exist"

    def forbidden(*args: object, **kwargs: object) -> object:
        raise AssertionError("target access occurred before V35 verification")

    monkeypatch.setattr(campaign.v35, "_acquire_model", forbidden)
    with pytest.raises(
        campaign.ConstructionK7Standard2048AdaptiveAccountedCampaignV36Error,
        match="V35 semantic predecessor",
    ):
        campaign.run_standard_2048_adaptive_accounted_campaign_v36(
            v35_campaign_bytes=b"{}",
            v35_verification_bytes=b"{}",
            output_root=output,
        )
    assert not output.exists()


def test_v36_source_reruns_operations_without_summary_translation() -> None:
    source = Path(campaign.__file__).read_text(encoding="utf-8")
    assert "ProcessPoolExecutor(max_workers=1)" in source
    assert "executor.submit(_accounted_episode, task)" in source
    assert "v35._episode" not in source
    assert "v35._campaign_document" not in source
    assert '"summary_to_counter_translation_used": False' in source


def test_worker_task_is_an_exact_canonical_object() -> None:
    task = campaign._worker_task_v36(  # noqa: SLF001
        episode_index=0,
        initial_board=(0,) * 16,
        execution_seed="0" * 64,
        overlay={},
        candidate={},
    )
    raw = canonical_json_bytes(task)
    assert loads_canonical_json(raw) == task
    assert task["schema"] == (
        "acfqp.standard_2048_adaptive_accounting_worker_task.v36"
    )
    assert task["adaptive_accounting_preregistration_id"] == (
        campaign.pre.PREREGISTRATION_ID
    )
    assert type(task["initial_board_ranks"]) is list
    board = campaign._domain_board_from_worker_task_v36(task)  # noqa: SLF001
    assert type(board) is tuple
    assert board == (0,) * 16


def test_campaign_wrapper_accepts_the_platform_path_subclass(tmp_path: Path) -> None:
    payload = {"schema": "test-only-wrapper-payload"}
    campaign_id = content_id(campaign.pre.FUTURE_DOMAINS["campaign"], payload)
    document = {**payload, "adaptive_accounted_campaign_id": campaign_id}
    value = campaign.Standard2048AdaptiveAccountedCampaignV36(
        campaign._ISSUER,  # noqa: SLF001
        canonical_json_bytes(document),
        campaign_id,
        tmp_path,
    )
    assert value.output_root == tmp_path


@pytest.fixture(scope="module")
def result():
    if not FULL:
        pytest.skip("requires frozen V35 bytes and preregistered V36 execution")
    value = campaign.run_standard_2048_adaptive_accounted_campaign_v36(
        v35_campaign_bytes=V35_CAMPAIGN_PATH.read_bytes(),
        v35_verification_bytes=V35_VERIFICATION_PATH.read_bytes(),
        output_root=V36_OUTPUT_ROOT,
    )
    return campaign.verify_standard_2048_adaptive_accounted_campaign_v36(value)


def test_v36_issues_native_vectors_for_every_lane(result) -> None:
    document = result.to_document()
    assert document["v35_native_replay_campaign_id"] == campaign.V35_CAMPAIGN_ID
    assert document["operational_work_vector_count"] == 15
    assert document["evaluation_work_vector_count"] >= 1
    assert document[
        "all_required_counter_leaves_have_explicit_native_records"
    ] is True
    assert document[
        "all_nine_shared_resource_paths_have_measurement_receipts"
    ] is True
    assert document["evaluation_replay_excluded_from_operational_comparison"] is True
    assert document["summary_to_counter_translation_used"] is False


def test_v36_sample_tax_and_claim_boundaries(result) -> None:
    document = result.to_document()
    assert document["operational_target_probability_label_query_count"] < document[
        "evaluation_no_prior_probability_label_count"
    ]
    assert document[
        "sample_tax_reduced_on_registered_first_failure_label_axis"
    ] is True
    assert document["formal_counter_completeness_candidate"] is True
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"


def test_campaign_identity_tamper_is_rejected(result) -> None:
    forged = copy.copy(result)
    object.__setattr__(forged, "campaign_id", "f" * 64)
    with pytest.raises(
        campaign.ConstructionK7Standard2048AdaptiveAccountedCampaignV36Error
    ):
        campaign.verify_standard_2048_adaptive_accounted_campaign_v36(forged)
