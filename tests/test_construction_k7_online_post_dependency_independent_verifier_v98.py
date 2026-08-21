import ast
import copy
import hashlib
from pathlib import Path

import pytest

from acfqp import construction_k7_online_post_dependency_independent_verifier_v98 as verifier
from acfqp.phase3e_ids import loads_canonical_json


CAMPAIGN_PATH = Path(
    ".tmp/exact-freeze/v98_online_post_dependency_campaign.json"
)


def test_v98_producer_free_verifier_rederives_activation_and_dependency_programs():
    raw = CAMPAIGN_PATH.read_bytes()
    result = verifier.verify_online_post_dependency_campaign_bytes_v98(raw)
    assert result["verification_status"] == (
        "REGISTERED_ONLINE_POST_DEPENDENCY_ACTIVATION_GATE_VERIFIED"
    )
    assert result["verified_accounting"][
        "meta_model_activation_target_labels_with_right_censoring"
    ] == 178
    assert result["verified_accounting"][
        "no_prior_model_activation_target_labels_with_right_censoring"
    ] == 206
    assert result["verified_accounting"]["activation_label_reduction"] == 28
    assert result[
        "post_dependency_program_rederived_from_raw_successor_differences"
    ] is True
    assert result["mdl_confidence_activation_rule_replayed_from_query_order"] is True
    assert result[
        "structural_prior_model_activation_sample_tax_advantage_verified"
    ] is True
    assert result["structural_prior_total_task_label_advantage_verified"] is False
    assert result["complete_world_model_synthesized"] is False
    assert result["official_execution_allowed"] is False


def test_v98_verification_artifact_is_content_addressed():
    raw = verifier.freeze_online_post_dependency_verification_v98(
        CAMPAIGN_PATH.read_bytes()
    )
    document = loads_canonical_json(raw)
    assert document["verification_id"] == verifier.VERIFICATION_ID
    assert len(raw) == verifier.EXPECTED_CANONICAL_BYTE_COUNT
    assert hashlib.sha256(raw).hexdigest() == verifier.EXPECTED_CANONICAL_SHA256


def test_v98_verifier_rejects_rehashed_early_activation_claim():
    campaign = loads_canonical_json(CAMPAIGN_PATH.read_bytes())
    occurrence = campaign["target_occurrences"][0]
    first = copy.deepcopy(
        occurrence["meta_prior_persistent_sequence"][
            "first_online_post_dependency_episode"
        ]
    )
    first["adaptive_stopping_history"][0]["activated"] = True
    payload = {key: value for key, value in first.items() if key != "episode_id"}
    first["episode_id"] = verifier._generic_id(  # noqa: SLF001
        verifier._ONLINE_EPISODE_DOMAIN, payload  # noqa: SLF001
    )
    with pytest.raises(Exception):
        verifier._check_first_episode(  # noqa: SLF001
            first,
            seed=occurrence["seed"],
            structural_prior_enabled=True,
            partial=occurrence["common_partial_acquisition"],
        )


def test_v98_verifier_rejects_campaign_byte_changes():
    raw = bytearray(CAMPAIGN_PATH.read_bytes())
    raw[len(raw) // 2] ^= 1
    with pytest.raises(Exception):
        verifier.verify_online_post_dependency_campaign_bytes_v98(bytes(raw))


def test_v98_verifier_has_no_producer_or_runtime_import():
    source = Path(verifier.__file__).read_text()
    tree = ast.parse(source)
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert not any("campaign_v98" in name for name in imported)
    assert not any("planner_v98" in name for name in imported)
    assert not any("sequence_v98" in name for name in imported)
