from __future__ import annotations

import ast
import copy
import os
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_standard_2048_adaptive_accounted_independent_verifier_v36 as verifier
from acfqp.phase3e_ids import canonical_json_bytes, content_id, loads_canonical_json


FULL = os.environ.get("ACFQP_RUN_ADAPTIVE_ACCOUNTING_V36") == "1"
V36_CAMPAIGN_PATH = Path(
    os.environ.get(
        "ACFQP_V36_CAMPAIGN_PATH",
        "/tmp/acfqp-v36-adaptive-accounted-campaign.canonical.json",
    )
)
V36_OUTPUT_ROOT = Path(
    os.environ.get(
        "ACFQP_V36_OUTPUT_ROOT", "/tmp/acfqp-v36-adaptive-accounting"
    )
)
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


def test_independent_verifier_import_surface_excludes_producers() -> None:
    source = Path(verifier.__file__).read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    forbidden = {
        "acfqp.construction_k7_standard_2048_adaptive_accounted_campaign_v36",
        "acfqp.construction_k7_standard_2048_adaptive_accounting_artifacts_v36",
        "acfqp.construction_k7_standard_2048_adaptive_accounting_runtime_v36",
        "acfqp.construction_k7_standard_2048_adaptive_expression_campaign_v35",
        "acfqp.construction_k7_standard_2048_adaptive_expression_runtime_v35",
        "acfqp.construction_k7_standard_2048_adaptive_expression_target_v35",
    }
    assert imported.isdisjoint(forbidden)


@pytest.fixture(scope="module")
def result():
    if not FULL:
        pytest.skip("requires retained V35 and V36 canonical bytes")
    verified = verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
        campaign_bytes=V36_CAMPAIGN_PATH.read_bytes(),
        output_root=V36_OUTPUT_ROOT,
        v35_campaign_bytes=V35_CAMPAIGN_PATH.read_bytes(),
        v35_verification_bytes=V35_VERIFICATION_PATH.read_bytes(),
    )
    return verified, V36_CAMPAIGN_PATH.read_bytes()


def test_every_vector_receipt_and_stage_replays(result) -> None:
    verified, _ = result
    document = verified.to_document()
    assert document["operational_work_vector_count"] == 15
    assert document["evaluation_work_vector_count"] == 5
    assert document["every_counter_record_and_native_zero_replayed"] is True
    assert document["every_operational_comparison_recomputed"] is True
    assert document["every_output_byte_fixed_point_replayed"] is True
    assert document[
        "failure_acquisition_proposal_proof_overlay_planning_and_execution_separate"
    ] is True


def test_sample_tax_and_claim_locks_replay(result) -> None:
    verified, _ = result
    document = verified.to_document()
    assert document[
        "registered_first_failure_label_axis_sample_tax_reduction_replayed"
    ] is True
    assert document["automatic_reusable_world_model_goal_completed"] is False
    assert document["broad_iid_or_cross_domain_sample_efficiency_claimed"] is False
    assert document["total_operational_work_saving_claimed"] is False
    assert document["official_execution_allowed"] is False
    assert document["official_scalar_cost"] is None
    assert document["official_N_break_even"] is None
    assert document["counter_completeness_gate_status"] == "NOT_RUN"
    assert document["workload_economics_gate_status"] == "NOT_RUN"


def test_retained_bundle_tamper_is_rejected(result, tmp_path: Path) -> None:
    _, campaign_bytes = result
    copied = tmp_path / "copied"
    shutil.copytree(V36_OUTPUT_ROOT, copied)
    victim = next(copied.rglob("episode-0000-planning-operational.json"))
    damaged = bytearray(victim.read_bytes())
    damaged[-2] ^= 1
    victim.write_bytes(bytes(damaged))
    with pytest.raises(
        verifier.ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error
    ):
        verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
            campaign_bytes=campaign_bytes,
            output_root=copied,
            v35_campaign_bytes=V35_CAMPAIGN_PATH.read_bytes(),
            v35_verification_bytes=V35_VERIFICATION_PATH.read_bytes(),
        )


def test_resigned_stage_merge_or_claim_flip_is_rejected(result) -> None:
    _, campaign_bytes = result
    document = loads_canonical_json(campaign_bytes)
    assert type(document) is dict
    for mutate in ("merge", "claim"):
        forged = copy.deepcopy(document)
        if mutate == "merge":
            forged["model_stage_bundles"].pop(2)
        else:
            forged["broad_iid_or_cross_domain_sample_efficiency_claimed"] = True
        payload = {
            key: value
            for key, value in forged.items()
            if key != "adaptive_accounted_campaign_id"
        }
        forged["adaptive_accounted_campaign_id"] = content_id(
            verifier.pre.FUTURE_DOMAINS["campaign"], payload
        )
        with pytest.raises(
            verifier.ConstructionK7Standard2048AdaptiveAccountedIndependentVerifierV36Error
        ):
            verifier.verify_standard_2048_adaptive_accounting_bytes_independently_v36(
                campaign_bytes=canonical_json_bytes(forged),
                output_root=V36_OUTPUT_ROOT,
                v35_campaign_bytes=V35_CAMPAIGN_PATH.read_bytes(),
                v35_verification_bytes=V35_VERIFICATION_PATH.read_bytes(),
            )
