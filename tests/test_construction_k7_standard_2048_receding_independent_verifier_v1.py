from __future__ import annotations

import ast
import copy
from pathlib import Path

import pytest

from acfqp import construction_k7_standard_2048_receding_independent_verifier_v1 as subject
from acfqp import construction_k7_standard_2048_receding_world_model_v1 as producer
from acfqp.phase3e_ids import canonical_json_bytes, content_id


@pytest.fixture(scope="module")
def campaign_bytes() -> bytes:
    return producer.run_standard_2048_receding_world_model_campaign_v1().canonical_bytes


def test_independent_replay_closes_standard_semantics_model_plan_and_direct(campaign_bytes) -> None:
    verification = subject.verify_standard_2048_receding_campaign_bytes_independently_v1(
        campaign_bytes
    ).to_document()
    assert verification["standard_4x4_semantics_replayed"] is True
    assert verification["h3_model_plans_replayed"] is True
    assert verification["matched_direct_replayed"] is True
    assert verification["heldout_d4_zero_ground_reuse_replayed"] is True
    assert verification["world_model_row_count"] == 173
    assert verification["direct_ground_row_count"] == 188
    assert verification["process_or_iid_authority_independently_verified"] is False
    assert verification["official_execution_allowed"] is False


def test_verifier_does_not_import_campaign_producer() -> None:
    tree = ast.parse(Path(subject.__file__).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imported.add(node.module)
            imported.update(alias.name for alias in node.names)
    assert producer.__name__ not in imported


def _resign_root(document: dict) -> bytes:
    payload = {key: value for key, value in document.items() if key != "campaign_id"}
    document["campaign_id"] = content_id(producer.DOMAINS["campaign"], payload)
    return canonical_json_bytes(document)


def test_fully_resigned_fake_zero_ground_reuse_is_rejected(campaign_bytes) -> None:
    attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
    attacked["heldout_reuse_incremental_ground_row_count"] = 1
    with pytest.raises(subject.ConstructionK7Standard2048IndependentVerifierV1Error):
        subject.verify_standard_2048_receding_campaign_bytes_independently_v1(
            _resign_root(attacked)
        )


def test_fully_resigned_row_probability_attack_is_rejected(campaign_bytes) -> None:
    attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
    row = attacked["final_world_model"]["rows"][0]
    row["outcomes"][0]["probability"] = {"numerator": 1, "denominator": 2}
    row_payload = {key: value for key, value in row.items() if key != "quotient_row_id"}
    row["quotient_row_id"] = content_id(producer.DOMAINS["row"], row_payload)
    model = attacked["final_world_model"]
    model_payload = {key: value for key, value in model.items() if key != "world_model_id"}
    model["world_model_id"] = content_id(producer.DOMAINS["model"], model_payload)
    with pytest.raises(subject.ConstructionK7Standard2048IndependentVerifierV1Error):
        subject.verify_standard_2048_receding_campaign_bytes_independently_v1(
            _resign_root(attacked)
        )


def test_fully_resigned_direct_work_understatement_is_rejected(campaign_bytes) -> None:
    attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
    direct = attacked["matched_direct_baseline"]["first_decision"]
    direct["ground_state_action_row_count"] -= 1
    direct_payload = {
        key: value for key, value in direct.items() if key != "matched_direct_plan_id"
    }
    direct["matched_direct_plan_id"] = content_id(producer.DOMAINS["direct"], direct_payload)
    attacked["matched_direct_baseline"]["total_ground_state_action_row_count"] -= 1
    with pytest.raises(subject.ConstructionK7Standard2048IndependentVerifierV1Error):
        subject.verify_standard_2048_receding_campaign_bytes_independently_v1(
            _resign_root(attacked)
        )


def test_claim_upgrade_and_unknown_fields_are_rejected(campaign_bytes) -> None:
    for mutation in (
        lambda row: row.__setitem__("full_standard_2048_game_completed", True),
        lambda row: row.__setitem__("forged", True),
    ):
        attacked = copy.deepcopy(__import__("json").loads(campaign_bytes))
        mutation(attacked)
        with pytest.raises(subject.ConstructionK7Standard2048IndependentVerifierV1Error):
            subject.verify_standard_2048_receding_campaign_bytes_independently_v1(
                _resign_root(attacked)
            )
