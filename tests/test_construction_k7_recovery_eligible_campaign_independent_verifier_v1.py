from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import shutil

import pytest

from acfqp import construction_k7_recovery_eligible_campaign_independent_verifier_v1 as subject
from acfqp.phase3e_ids import (
    CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN,
    PHASE3E_DOMAIN_TAGS,
    canonical_json_bytes,
    content_id,
)


def test_verifier_surface_and_domain_are_additive() -> None:
    assert subject.VERIFICATION_DOMAIN in PHASE3E_DOMAIN_TAGS
    assert set(subject.__all__) == {
        "ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error",
        "RecoveryEligibleCampaignDirectoryVerificationV1",
        "verify_recovery_eligible_campaign_directory_bytes_v1",
    }


def test_verifier_imports_no_recovery_producer_or_planner() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            imported.update(f"{node.module}.{alias.name}" for alias in node.names)
    forbidden = {
        "acfqp.construction_k7_recovery_eligible_preregistered_campaign_v1",
        "acfqp.construction_k7_recovery_eligible_occurrence_accounting_v1",
        "acfqp.construction_k7_recovery_eligible_supervised_executor_v1",
        "acfqp.construction_k7_recovery_eligible_accounted_runtime_v1",
        "acfqp.construction_k7_recovery_eligible_world_model_loop_v1",
        "acfqp.construction_k7_recovery_eligible_direct_fallback_v1",
    }
    assert not forbidden.intersection(imported)


def test_verifier_rejects_absent_directory(tmp_path: Path) -> None:
    with pytest.raises(
        (FileNotFoundError, subject.ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error)
    ):
        subject.verify_recovery_eligible_campaign_directory_bytes_v1(
            tmp_path / "absent",
            expected_preregistration_id="0" * 64,
            expected_closure_id="1" * 64,
        )


@pytest.fixture(scope="module")
def retained_campaign():
    directory = os.environ.get("ACFQP_RETAINED_RECOVERY_ELIGIBLE_CAMPAIGN")
    preregistration_id = os.environ.get("ACFQP_RECOVERY_CAMPAIGN_PREREGISTRATION_ID")
    closure_id = os.environ.get("ACFQP_RECOVERY_CAMPAIGN_CLOSURE_ID")
    if not directory or not preregistration_id or not closure_id:
        pytest.skip("retained recovery campaign is disabled")
    return Path(directory), preregistration_id, closure_id


def test_real_bytes_only_replay_closes_two_occurrences(retained_campaign) -> None:
    directory, preregistration_id, closure_id = retained_campaign
    result = subject.verify_recovery_eligible_campaign_directory_bytes_v1(
        directory,
        expected_preregistration_id=preregistration_id,
        expected_closure_id=closure_id,
    )
    document = result.to_document()
    assert document["logical_occurrence_count"] == 2
    assert len(document["ordered_occurrence_accounting_bundle_ids"]) == 2
    assert document["bytes_only_replay"] is True
    assert document["producer_imported"] is False
    assert document["planner_or_ground_kernel_invoked"] is False
    assert document["full_registered_denominator_recomputed"] is True
    assert document["campaign_orchestration_work_vector_issued"] is False
    assert document["official_execution_allowed"] is False


def test_real_bytes_verifier_rejects_swapped_occurrence_rows(
    retained_campaign, tmp_path: Path
) -> None:
    directory, preregistration_id, closure_id = retained_campaign
    copied = tmp_path / "swapped"
    shutil.copytree(directory, copied)
    first = (copied / "OCCURRENCE_0001_ROW.json").read_bytes()
    second = (copied / "OCCURRENCE_0002_ROW.json").read_bytes()
    (copied / "OCCURRENCE_0001_ROW.json").write_bytes(second)
    (copied / "OCCURRENCE_0002_ROW.json").write_bytes(first)
    with pytest.raises(subject.ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error):
        subject.verify_recovery_eligible_campaign_directory_bytes_v1(
            copied,
            expected_preregistration_id=preregistration_id,
            expected_closure_id=closure_id,
        )


def test_real_bytes_verifier_rejects_resigned_closure_claim_flip(
    retained_campaign, tmp_path: Path
) -> None:
    directory, preregistration_id, _closure_id = retained_campaign
    copied = tmp_path / "claim-flip"
    shutil.copytree(directory, copied)
    target = copied / "CAMPAIGN_CLOSURE.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    document["campaign_orchestration_work_vector_issued"] = True
    payload = dict(document)
    payload.pop("campaign_closure_id")
    forged_id = content_id(
        CONSTRUCTION_K7_RECOVERY_ELIGIBLE_CAMPAIGN_CLOSURE_V1_DOMAIN,
        payload,
    )
    document["campaign_closure_id"] = forged_id
    target.write_bytes(canonical_json_bytes(document))
    with pytest.raises(subject.ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error):
        subject.verify_recovery_eligible_campaign_directory_bytes_v1(
            copied,
            expected_preregistration_id=preregistration_id,
            expected_closure_id=forged_id,
        )


def test_real_bytes_verifier_rejects_occurrence_artifact_tamper(
    retained_campaign, tmp_path: Path
) -> None:
    directory, preregistration_id, closure_id = retained_campaign
    copied = tmp_path / "artifact-tamper"
    shutil.copytree(directory, copied)
    target = copied / "occurrence-0001" / "TERMINAL_ARTIFACT.json"
    document = json.loads(target.read_text(encoding="utf-8"))
    document["terminal_code"] = "ABSTRACT_CERTIFIED"
    target.write_bytes(canonical_json_bytes(document))
    with pytest.raises(subject.ConstructionK7RecoveryEligibleCampaignIndependentVerifierV1Error):
        subject.verify_recovery_eligible_campaign_directory_bytes_v1(
            copied,
            expected_preregistration_id=preregistration_id,
            expected_closure_id=closure_id,
        )

